ROLE_LABELS = {
    "student_faculty": "Student / Faculty",
    "technician": "Technician",
    "department_manager": "Department Manager",
    "facilities_admin": "Facilities Administrator",
    "procurement_approver": "Procurement Approver",
    "system_admin": "System Administrator",
}


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role.replace("_", " ").title())