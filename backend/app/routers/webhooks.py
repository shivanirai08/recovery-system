import json
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from app.db import get_db
from app.utils.webhook_verify import verify_razorpay_signature

router = APIRouter(tags=["webhooks"])

HANDLED_EVENTS = {
    "payment_link.paid",
    "payment.failed",
    "payment_link.expired",
}


def _entity(payload: dict, name: str) -> dict:
    block = payload.get(name) or {}
    return block.get("entity") or {}


def _find_payment(db, payload: dict) -> dict | None:
    payment_link = _entity(payload, "payment_link")
    payment = _entity(payload, "payment")
    notes = payment_link.get("notes") or payment.get("notes") or {}

    recoverai_id = notes.get("recoverai_payment_id")
    if recoverai_id and ObjectId.is_valid(str(recoverai_id)):
        doc = db["payments"].find_one({"_id": ObjectId(str(recoverai_id))})
        if doc:
            return doc

    link_id = payment_link.get("id") or payment.get("payment_link_id")
    if link_id:
        doc = db["payments"].find_one({"razorpay_payment_link_id": link_id})
        if doc:
            return doc

    reference_id = payment_link.get("reference_id")
    if reference_id:
        return db["payments"].find_one({"reference_id": reference_id})
    return None


def _status_for_event(event: str) -> str | None:
    if event == "payment_link.paid":
        return "paid"
    if event == "payment.failed":
        return "failed"
    if event == "payment_link.expired":
        return "expired"
    return None


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    try:
        verify_razorpay_signature(raw_body, request.headers.get("X-Razorpay-Signature"))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        body = json.loads(raw_body.decode())
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Invalid JSON") from exc

    event = body.get("event")
    payload = body.get("payload") or {}
    payment_entity = _entity(payload, "payment")
    link_entity = _entity(payload, "payment_link")
    event_id = (
        request.headers.get("X-Razorpay-Event-Id")
        or f"{event}:{payment_entity.get('id') or link_entity.get('id')}:{body.get('created_at')}"
    )

    db = get_db()
    existing = db["webhook_events"].find_one({"event_id": event_id})
    if existing:
        return {"status": "ignored", "reason": "duplicate", "event_id": event_id}

    try:
        db["webhook_events"].insert_one({
            "event_id": event_id,
            "event": event,
            "payload": body,
            "received_at": datetime.now(timezone.utc),
            "processed": False,
        })
    except DuplicateKeyError:
        return {"status": "ignored", "reason": "duplicate", "event_id": event_id}

    if event not in HANDLED_EVENTS:
        return {"status": "ignored", "reason": "unhandled_event", "event": event}

    payment_doc = _find_payment(db, payload)
    if not payment_doc:
        return {"status": "ignored", "reason": "payment_not_found", "event": event}

    # Successful pay must not be overwritten by a later failed webhook.
    if payment_doc.get("status") == "paid":
        db["webhook_events"].update_one(
            {"event_id": event_id},
            {"$set": {"processed": True, "skipped": "already_paid"}},
        )
        return {"status": "ignored", "reason": "already_paid", "event": event}

    now = datetime.now(timezone.utc)
    update = {
        "status": _status_for_event(event),
        "updated_at": now,
        "last_razorpay_event": event,
        "razorpay_payment_id": payment_entity.get("id"),
        "last_error": payment_entity.get("error_description"),
    }
    db["payments"].update_one({"_id": payment_doc["_id"]}, {"$set": update})
    db["webhook_events"].update_one(
        {"event_id": event_id},
        {"$set": {"processed": True, "payment_id": str(payment_doc["_id"])}},
    )
    return {
        "status": "ok",
        "event": event,
        "payment_id": str(payment_doc["_id"]),
        "new_status": update["status"],
    }
