
"""Unit tests for delivery management in Finmarket Kart Essentials."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.services.delivery_service import DeliveryService


@pytest.fixture
def db():
    """Provide a mocked database session."""
    return MagicMock()


@pytest.fixture
def service(db, monkeypatch):
    """Create DeliveryService with a mocked repository."""
    repository = MagicMock()

    monkeypatch.setattr(
        "backend.services.delivery_service.DeliveryRepository",
        lambda session: repository,
    )

    instance = DeliveryService(db)
    instance.repository = repository

    return instance


# =========================================================
# COMMON DATA VALIDATION
# =========================================================

def test_data_dict_accepts_dictionary():
    data = {"partner_code": "DHL001"}

    result = DeliveryService._data_dict(data)

    assert result == data
    assert result is not data


def test_data_dict_rejects_invalid_input():
    with pytest.raises(TypeError, match="Invalid delivery data"):
        DeliveryService._data_dict("invalid")


def test_data_dict_accepts_pydantic_model():
    class SampleSchema:
        def model_dump(self, exclude_unset=True):
            return {"partner_code": "DHL001"}

    result = DeliveryService._data_dict(SampleSchema())

    assert result == {"partner_code": "DHL001"}


# =========================================================
# DELIVERY PARTNER TESTS
# =========================================================

def test_create_delivery_partner_success(service, db):
    partner = SimpleNamespace(
        id=1,
        partner_code="DHL001",
    )

    service.repository.get_delivery_partner_by_code.return_value = None
    service.repository.create_delivery_partner.return_value = partner

    result = service.create_delivery_partner(
        {"partner_code": " DHL001 "}
    )

    assert result is partner

    service.repository.create_delivery_partner.assert_called_once_with(
        {"partner_code": "DHL001"}
    )

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_create_delivery_partner_rejects_missing_code(service, db):
    with pytest.raises(
        ValueError,
        match="Delivery partner code is required",
    ):
        service.create_delivery_partner({})

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_create_delivery_partner_rejects_empty_code(service, db):
    with pytest.raises(
        ValueError,
        match="Delivery partner code cannot be empty",
    ):
        service.create_delivery_partner(
            {"partner_code": "   "}
        )

    db.rollback.assert_called_once()


def test_create_delivery_partner_rejects_duplicate_code(service, db):
    service.repository.get_delivery_partner_by_code.return_value = (
        SimpleNamespace(id=1)
    )

    with pytest.raises(
        ValueError,
        match="Delivery partner code already exists",
    ):
        service.create_delivery_partner(
            {"partner_code": "DHL001"}
        )

    service.repository.create_delivery_partner.assert_not_called()
    db.rollback.assert_called_once()


def test_get_delivery_partner_success(service):
    partner = SimpleNamespace(id=1)

    service.repository.get_delivery_partner.return_value = partner

    result = service.get_delivery_partner(1)

    assert result is partner


def test_get_delivery_partner_not_found(service):
    service.repository.get_delivery_partner.return_value = None

    with pytest.raises(
        ValueError,
        match="Delivery partner not found",
    ):
        service.get_delivery_partner(999)


def test_get_available_delivery_partners(service):
    partners = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]

    service.repository.get_available_delivery_partners.return_value = (
        partners,
        2,
    )

    result, total = service.get_available_delivery_partners(
        page=1,
        page_size=20,
    )

    assert result == partners
    assert total == 2

    service.repository.get_available_delivery_partners.assert_called_once_with(
        page=1,
        page_size=20,
    )


def test_inactive_partner_cannot_be_made_available(service, db):
    partner = SimpleNamespace(
        id=1,
        is_active=False,
    )

    service.repository.get_delivery_partner.return_value = partner

    with pytest.raises(
        ValueError,
        match="Inactive delivery partner cannot be made available",
    ):
        service.set_partner_availability(1, True)

    service.repository.set_partner_availability.assert_not_called()
    db.rollback.assert_called_once()


# =========================================================
# SERVICEABLE PINCODE TESTS
# =========================================================

def test_create_serviceable_pincode_success(service, db):
    record = SimpleNamespace(
        id=1,
        pincode="500001",
    )

    db.scalars.return_value.first.return_value = None

    service.repository.create_serviceable_pincode.return_value = record

    result = service.create_serviceable_pincode(
        {"pincode": " 500001 "}
    )

    assert result is record

    service.repository.create_serviceable_pincode.assert_called_once_with(
        {"pincode": "500001"}
    )

    db.commit.assert_called_once()


def test_create_serviceable_pincode_rejects_empty_value(service, db):
    with pytest.raises(
        ValueError,
        match="Pincode is required",
    ):
        service.create_serviceable_pincode(
            {"pincode": " "}
        )

    db.rollback.assert_called_once()


def test_create_serviceable_pincode_rejects_duplicate(service, db):
    db.scalars.return_value.first.return_value = SimpleNamespace(
        pincode="500001"
    )

    with pytest.raises(
        ValueError,
        match="Pincode is already registered",
    ):
        service.create_serviceable_pincode(
            {"pincode": "500001"}
        )

    service.repository.create_serviceable_pincode.assert_not_called()
    db.rollback.assert_called_once()


def test_check_pincode_serviceability_available(service):
    service.repository.check_pincode_serviceability.return_value = {
        "pincode": "500001",
        "is_serviceable": True,
    }

    result = service.check_pincode_serviceability("500001")

    assert result["is_serviceable"] is True

    assert result["message"] == (
        "Delivery is available for this pincode."
    )


def test_check_pincode_serviceability_unavailable(service):
    service.repository.check_pincode_serviceability.return_value = {
        "pincode": "500002",
        "is_serviceable": False,
    }

    result = service.check_pincode_serviceability("500002")

    assert result["is_serviceable"] is False

    assert result["message"] == (
        "Sorry, delivery is not available for this pincode."
    )


# =========================================================
# DELIVERY SLOT TESTS
# =========================================================

def test_create_delivery_slot_success(service, db):
    slot_data = {
        "delivery_date": date.today() + timedelta(days=1),
        "start_time": "09:00",
        "end_time": "12:00",
        "capacity": 10,
    }

    slot = SimpleNamespace(id=1)

    db.scalars.return_value.first.return_value = None

    service.repository.create_delivery_slot.return_value = slot

    result = service.create_delivery_slot(slot_data)

    assert result is slot

    service.repository.create_delivery_slot.assert_called_once_with(
        slot_data
    )

    db.commit.assert_called_once()


def test_create_delivery_slot_rejects_past_date(service, db):
    slot_data = {
        "delivery_date": date.today() - timedelta(days=1),
        "start_time": "09:00",
        "end_time": "12:00",
        "capacity": 10,
    }

    with pytest.raises(
        ValueError,
        match="Delivery slot date cannot be in the past",
    ):
        service.create_delivery_slot(slot_data)

    service.repository.create_delivery_slot.assert_not_called()
    db.rollback.assert_called_once()


def test_create_delivery_slot_rejects_overlap(service, db):
    slot_data = {
        "delivery_date": date.today() + timedelta(days=1),
        "start_time": "10:00",
        "end_time": "13:00",
        "capacity": 10,
    }

    db.scalars.return_value.first.return_value = SimpleNamespace(
        id=10
    )

    with pytest.raises(
        ValueError,
        match="Delivery slot overlaps",
    ):
        service.create_delivery_slot(slot_data)

    service.repository.create_delivery_slot.assert_not_called()
    db.rollback.assert_called_once()


def test_get_delivery_slot_not_found(service):
    service.repository.get_delivery_slot.return_value = None

    with pytest.raises(
        ValueError,
        match="Delivery slot not found",
    ):
        service.get_delivery_slot(999)


def test_get_available_delivery_slots_rejects_past_date(service):
    past_date = date.today() - timedelta(days=1)

    with pytest.raises(
        ValueError,
        match="Cannot retrieve slots for a past date",
    ):
        service.get_available_delivery_slots(past_date)

    service.repository.get_available_delivery_slots.assert_not_called()


# =========================================================
# SHIPMENT CREATION TESTS
# =========================================================

def test_create_shipment_success(service, db):
    order = SimpleNamespace(id=10)

    shipment = SimpleNamespace(
        id=20,
        status="created",
    )

    db.get.return_value = order

    service.repository.get_shipment_by_order_id.return_value = None

    service.repository.create_shipment.return_value = shipment

    service.repository.get_shipment_by_id.return_value = shipment

    result = service.create_shipment(
        {"order_id": 10}
    )

    assert result is shipment

    # Verify the tracking number generated by the service.
    created_payload = (
        service.repository.create_shipment.call_args.args[0]
    )

    assert created_payload["tracking_number"].startswith("FMK")
    assert len(created_payload["tracking_number"]) == 23

    service.repository.add_tracking_event.assert_called_once_with(
        shipment_id=20,
        status="created",
        description="Shipment created successfully.",
        updated_by="system",
    )

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_create_shipment_rejects_missing_order_id(service, db):
    with pytest.raises(
        ValueError,
        match="Order ID is required",
    ):
        service.create_shipment({})

    db.rollback.assert_called_once()


def test_create_shipment_rejects_unknown_order(service, db):
    db.get.return_value = None

    with pytest.raises(
        ValueError,
        match="Order not found",
    ):
        service.create_shipment(
            {"order_id": 999}
        )

    service.repository.create_shipment.assert_not_called()
    db.rollback.assert_called_once()


def test_create_shipment_rejects_duplicate_order(service, db):
    db.get.return_value = SimpleNamespace(id=10)

    service.repository.get_shipment_by_order_id.return_value = (
        SimpleNamespace(id=20)
    )

    with pytest.raises(
        ValueError,
        match="A shipment already exists for this order",
    ):
        service.create_shipment(
            {"order_id": 10}
        )

    service.repository.create_shipment.assert_not_called()
    db.rollback.assert_called_once()


# =========================================================
# SHIPMENT STATUS TESTS
# =========================================================

def test_update_shipment_status_success(service, db):
    shipment = SimpleNamespace(
        id=20,
        status="assigned",
    )

    updated_shipment = SimpleNamespace(
        id=20,
        status="picked_up",
    )

    service.repository.get_shipment_by_id.side_effect = [
        shipment,
        updated_shipment,
    ]

    service.repository.update_shipment_status.return_value = (
        updated_shipment
    )

    result = service.update_shipment_status(
        shipment_id=20,
        status="picked_up",
        description="Package picked up",
        location="Hyderabad",
        updated_by="delivery-partner-1",
    )

    assert result is updated_shipment

    service.repository.update_shipment_status.assert_called_once_with(
        shipment_id=20,
        status="picked_up",
        failure_reason=None,
        delivery_proof_url=None,
    )

    service.repository.add_tracking_event.assert_called_once_with(
        shipment_id=20,
        status="picked_up",
        description="Package picked up",
        location="Hyderabad",
        updated_by="delivery-partner-1",
    )

    db.commit.assert_called_once()


def test_update_shipment_status_rejects_invalid_transition(
    service,
    db,
):
    shipment = SimpleNamespace(
        id=20,
        status="created",
    )

    service.repository.get_shipment_by_id.return_value = shipment

    with pytest.raises(
        ValueError,
        match="Cannot change shipment status",
    ):
        service.update_shipment_status(
            shipment_id=20,
            status="delivered",
            description="Delivered",
        )

    service.repository.update_shipment_status.assert_not_called()

    service.repository.add_tracking_event.assert_not_called()

    db.rollback.assert_called_once()


def test_update_shipment_status_rejects_unknown_shipment(
    service,
    db,
):
    service.repository.get_shipment_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="Shipment not found",
    ):
        service.update_shipment_status(
            shipment_id=999,
            status="assigned",
            description="Assigned",
        )

    db.rollback.assert_called_once()


def test_failed_shipment_uses_description_as_failure_reason(
    service,
    db,
):
    shipment = SimpleNamespace(
        id=20,
        status="assigned",
    )

    updated_shipment = SimpleNamespace(
        id=20,
        status="failed",
    )

    service.repository.get_shipment_by_id.side_effect = [
        shipment,
        updated_shipment,
    ]

    service.repository.update_shipment_status.return_value = (
        updated_shipment
    )

    service.update_shipment_status(
        shipment_id=20,
        status="failed",
        description="Customer unavailable",
    )

    service.repository.update_shipment_status.assert_called_once_with(
        shipment_id=20,
        status="failed",
        failure_reason="Customer unavailable",
        delivery_proof_url=None,
    )


# =========================================================
# TRACKING TESTS
# =========================================================

def test_add_tracking_event_success(service, db):
    shipment = SimpleNamespace(id=20)

    event = SimpleNamespace(
        id=30,
        status="in_transit",
    )

    service.repository.get_shipment_by_id.return_value = shipment

    service.repository.add_tracking_event.return_value = event

    result = service.add_tracking_event(
        20,
        {
            "status": "in_transit",
            "description": "Package is moving",
            "location": "Hyderabad",
            "updated_by": "partner-1",
        },
    )

    assert result is event

    service.repository.add_tracking_event.assert_called_once_with(
        shipment_id=20,
        status="in_transit",
        description="Package is moving",
        location="Hyderabad",
        updated_by="partner-1",
        event_time=None,
    )

    db.commit.assert_called_once()


def test_get_shipment_tracking_success(service):
    shipment = SimpleNamespace(id=20)

    events = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]

    service.repository.get_shipment_by_id.return_value = shipment

    service.repository.get_shipment_tracking.return_value = events

    result = service.get_shipment_tracking(20)

    assert result == events


def test_get_shipment_tracking_rejects_unknown_shipment(service):
    service.repository.get_shipment_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="Shipment not found",
    ):
        service.get_shipment_tracking(999)


# =========================================================
# TRANSACTION TESTS
# =========================================================

def test_create_delivery_partner_rolls_back_on_repository_error(
    service,
    db,
):
    service.repository.get_delivery_partner_by_code.return_value = None

    service.repository.create_delivery_partner.side_effect = (
        RuntimeError("Database error")
    )

    with pytest.raises(
        RuntimeError,
        match="Database error",
    ):
        service.create_delivery_partner(
            {"partner_code": "DHL001"}
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
