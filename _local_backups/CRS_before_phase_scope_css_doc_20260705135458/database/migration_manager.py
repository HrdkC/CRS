from database.create_schema_version_table import (
    create_schema_version_table
)

from database.create_tbm_family_table import (
    create_tbm_family_table
)

from database.create_tbm_machine_table import (
    create_tbm_machine_table
)

from database.create_machine_stage_table import (
    create_machine_stage_table
)

from database.create_plc_registry_table import (
    create_plc_registry_table
)

from database.create_template_master_table import (
    create_template_master_table
)

from database.create_template_parameter_table import (
    create_template_parameter_table
)

from database.create_phase_control_master_table import (
    create_phase_control_master_table
)

from database.create_phase_control_option_table import (
    create_phase_control_option_table
)

from database.create_phase_control_mapping_table import (
    create_phase_control_mapping_table
)

from database.create_system_settings_table import (
    create_system_settings_table
)

from database.create_plc_program_history_table import (
    create_plc_program_history_table
)

from database.create_recipe_download_history_table import (
    create_recipe_download_history_table
)

from database.upgrade_recipes_test_only import (
    upgrade_recipes_test_only
)

class MigrationManager:

    @staticmethod
    def run_all():

        create_schema_version_table()

        create_tbm_family_table()

        create_tbm_machine_table()

        create_machine_stage_table()

        create_plc_registry_table()
        
        create_plc_program_history_table()

        create_template_master_table()

        create_template_parameter_table()

        create_phase_control_master_table()

        create_phase_control_option_table()

        create_phase_control_mapping_table()

        create_system_settings_table()
        
        create_recipe_download_history_table()

        upgrade_recipes_test_only()

        print(
            "All Database Migrations Completed"
        )
