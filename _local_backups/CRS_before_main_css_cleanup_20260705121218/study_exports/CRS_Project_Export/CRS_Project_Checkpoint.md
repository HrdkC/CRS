
Centralized Recipe System - Project Checkpoint

ACTIVE TABLES
- recipes
- recipe_parameter_values
- parameter_definitions
- recipe_phase_control
- recipe_status_history
- recipe_download_history

LEGACY TABLES (DO NOT USE FOR NEW DEVELOPMENT)
- recipe_master
- recipe_parameters
- recipe_versions
- recipe_version_values

WORKFLOW
DRAFT -> REVIEW -> APPROVED -> AUTO RELEASED

COPY RECIPE FEATURE COMPLETED
- Creates new recipe code
- Version = 1
- Status = DRAFT
- Copies recipe_parameter_values
- Copies recipe_phase_control
- Creates recipe_status_history entry

VERIFIED
- 119 parameter values copied
- 12 phase control rows copied

CURRENT BLOCKING ISSUE
AttributeError:
RecipeApprovalManager.update_status

Need to inspect:
- database/recipe_approval_manager.py
- recipe_editor_routes.py

NEXT PRIORITIES
1. Fix workflow integration
2. Workflow buttons
3. Workflow history screen
4. Dashboard alerts
5. Create Version feature
6. PLC Download Manager V2
7. PLC Upload
8. User management
9. Auto logout
10. Disaster recovery

IMPORTANT DECISIONS
- New architecture is source of truth.
- Keep legacy tables for now.
- Do not rename legacy tables yet.
