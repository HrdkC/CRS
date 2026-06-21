from database.audit_manager import AuditManager

history = AuditManager.get_audit_history()

for row in history:

    if row["action"] == "PARAMETER_CHANGED":

        print(row)
