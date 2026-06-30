"""Finance persona taxonomy mapped onto the enforced tenant role hierarchy."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.rbac import UserRole

_PERSONAS: tuple[dict[str, Any], ...] = (
    {
        "id": "owner_admin",
        "label": "Owner/Admin",
        "mapped_roles": [UserRole.owner.value, UserRole.admin.value],
        "description": "Tenant and finance operations administrator.",
        "areas": ["Settings", "Approval policy", "Agent controls", "Final approvals"],
        "allowed_actions": [
            "Configure tenant controls and AI operations",
            "Approve admin-threshold finance work",
            "Review all finance records and audit evidence",
        ],
        "restricted_actions": ["Tenant-scoped only; owner role is still required for owner-only actions"],
        "read_only": False,
    },
    {
        "id": "controller",
        "label": "Controller",
        "mapped_roles": [UserRole.admin.value, UserRole.owner.value],
        "description": "Record-to-report owner for close, journals, and statements.",
        "areas": ["Accounting", "Close", "Reports", "Audit"],
        "allowed_actions": [
            "Approve accounting and money-out work within policy",
            "Post and review journals through guarded accounting flows",
            "Inspect financial statements and decision timelines",
        ],
        "restricted_actions": ["Cannot bypass owner-threshold policy or tenant boundaries"],
        "read_only": False,
    },
    {
        "id": "cfo",
        "label": "CFO",
        "mapped_roles": [UserRole.owner.value, UserRole.admin.value],
        "description": "Executive finance owner for policy, performance, and approvals.",
        "areas": ["Management reporting", "Approval policy", "Cash", "Audit"],
        "allowed_actions": [
            "Inspect all finance reports and operational health",
            "Approve elevated finance work within the configured tenant policy",
            "Review AI Finance Ops Manager summaries and decision evidence",
        ],
        "restricted_actions": ["Owner-only tenant administration still requires owner role"],
        "read_only": False,
    },
    {
        "id": "finance_approver",
        "label": "Finance Approver",
        "mapped_roles": [
            UserRole.approver.value,
            UserRole.manager.value,
            UserRole.admin.value,
            UserRole.owner.value,
        ],
        "description": "Dedicated reviewer for manager-threshold Inbox decisions.",
        "areas": ["Inbox", "Approval controls", "Decision evidence"],
        "allowed_actions": [
            "Approve, approve with edits, or reject manager-threshold review work",
            "Inspect policy reasons and pending work that needs a higher approver",
        ],
        "restricted_actions": [
            "Cannot create or mutate operational records outside review actions",
            "Cannot approve admin or owner-threshold money-out, accounting, or high-risk work",
        ],
        "read_only": False,
    },
    {
        "id": "procurement_manager",
        "label": "Procurement Manager",
        "mapped_roles": [UserRole.manager.value, UserRole.admin.value, UserRole.owner.value],
        "description": "Procurement owner for purchase requests, orders, vendors, and AP matching.",
        "areas": ["Procurement", "Bills", "Pay Bills", "Vendor onboarding"],
        "allowed_actions": [
            "Create and convert purchase requests, purchase orders, and service orders",
            "Review vendor and procurement exceptions routed through Inbox",
            "Prepare payment and purchasing packets for approval",
        ],
        "restricted_actions": ["Cannot approve admin or owner-threshold spend unless mapped to admin/owner"],
        "read_only": False,
    },
    {
        "id": "ap_lead",
        "label": "AP Lead",
        "mapped_roles": [UserRole.manager.value, UserRole.admin.value, UserRole.owner.value],
        "description": "Procure-to-pay operator for vendors, bills, and payment preparation.",
        "areas": ["Bills", "Procurement", "Pay Bills", "AP Aging"],
        "allowed_actions": [
            "Create and review bills and procurement documents",
            "Prepare payment batches for approval",
            "Resolve vendor invoice exceptions routed through Inbox",
        ],
        "restricted_actions": ["Cannot approve admin or owner-threshold money-out work"],
        "read_only": False,
    },
    {
        "id": "ar_lead",
        "label": "AR Lead",
        "mapped_roles": [UserRole.manager.value, UserRole.admin.value, UserRole.owner.value],
        "description": "Order-to-cash operator for invoices, collections, and receipts.",
        "areas": ["Invoices", "Collections", "Reports", "Inbox"],
        "allowed_actions": [
            "Draft and review invoices",
            "Prepare collections communications for approval",
            "Inspect AR Aging, WIP, and revenue reports",
        ],
        "restricted_actions": ["Cannot bypass send, payment, or admin-threshold approval gates"],
        "read_only": False,
    },
    {
        "id": "auditor",
        "label": "Auditor",
        "mapped_roles": [UserRole.auditor.value],
        "description": "Read-only audit reviewer for records, reports, and decision evidence.",
        "areas": ["Reports", "Bills", "Invoices", "Audit evidence"],
        "allowed_actions": [
            "Inspect permitted tenant records and record-scoped decision timelines",
            "Review Inbox decision history and safe audit metadata",
        ],
        "restricted_actions": [
            "Cannot create, approve, edit, reject, post, pay, send, lock, or change settings",
            "Cannot export admin-only audit ledgers",
        ],
        "read_only": True,
    },
    {
        "id": "executive",
        "label": "Executive",
        "mapped_roles": [UserRole.viewer.value],
        "description": "Read-only leader reviewing operational and financial status.",
        "areas": ["Reports", "Management cockpit", "Action queues"],
        "allowed_actions": [
            "Inspect dashboards, reports, record details, and status evidence",
            "Review AI Finance Ops Manager summaries without mutating records",
        ],
        "restricted_actions": [
            "Cannot create, approve, edit, reject, post, pay, send, lock, or change settings",
        ],
        "read_only": True,
    },
)


def finance_persona_catalog() -> list[dict[str, Any]]:
    """Return a defensive copy of the finance persona taxonomy."""
    return deepcopy(list(_PERSONAS))


def persona_ids_for_role(role: UserRole) -> list[str]:
    """Return product-facing finance personas compatible with an enforced role."""
    return [
        str(persona["id"])
        for persona in _PERSONAS
        if role.value in set(persona["mapped_roles"])
    ]
