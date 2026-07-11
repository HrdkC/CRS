from database.audit_manager import AuditManager

history = AuditManager.get_audit_history(
    limit=20
)

for row in history:

    print(row)