from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    text
)

from database.sqlalchemy_db import (
    Base
)


class DictMixin:

    def to_dict(self):

        return {
            column.name: getattr(
                self,
                column.name
            )
            for column in self.__table__.columns
        }


class TBMFamily(Base, DictMixin):

    __tablename__ = "tbm_families"

    id = Column(Integer, primary_key=True)
    family_name = Column(Text, nullable=False)
    description = Column(Text)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(Text)


class TBMMachine(Base, DictMixin):

    __tablename__ = "tbm_machines"

    id = Column(Integer, primary_key=True)
    machine_code = Column(Text, nullable=False)
    family_id = Column(Integer, nullable=False)
    description = Column(Text)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(Text)


class MachineStage(Base, DictMixin):

    __tablename__ = "machine_stages"

    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    stage_type = Column(Text, nullable=False)
    description = Column(Text)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class Recipe(Base, DictMixin):

    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    stage_id = Column(Integer, nullable=False)
    recipe_code = Column(Text, nullable=False)
    recipe_name = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, server_default=text("1"))
    status = Column(Text, nullable=False, server_default=text("'DRAFT'"))
    created_by = Column(Text)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class ParameterDefinition(Base, DictMixin):

    __tablename__ = "parameter_definitions"

    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    stage_id = Column(Integer, nullable=False)
    tag_index = Column(Integer, nullable=False)
    plc_array_index = Column(Integer)
    parameter_name = Column(Text, nullable=False)
    parameter_class = Column(Text)
    unit = Column(Text)
    min_value = Column(Float)
    max_value = Column(Float)
    default_value = Column(Float)
    datatype = Column(Text, server_default=text("'REAL'"))
    english_memo = Column(Text)
    used = Column(Integer, server_default=text("1"))
    created_by = Column(Text)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime)


class RecipeParameterValue(Base, DictMixin):

    __tablename__ = "recipe_parameter_values"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, nullable=False)
    parameter_definition_id = Column(Integer, nullable=False)
    parameter_value = Column(Float)
    is_modified = Column(Integer, server_default=text("0"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class RecipePhaseControl(Base, DictMixin):

    __tablename__ = "recipe_phase_control"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, nullable=False)
    line_no = Column(Integer, nullable=False)
    phase_control_id = Column(Integer)
    stop_option = Column(Text)
    position_option = Column(Text)
    sequence_no = Column(Integer)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class RecipeStatusHistory(Base, DictMixin):

    __tablename__ = "recipe_status_history"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, nullable=False)
    recipe_code = Column(Text)
    old_status = Column(Text)
    new_status = Column(Text)
    changed_by = Column(Text)
    changed_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    remarks = Column(Text)


class RecipeDownloadHistory(Base, DictMixin):

    __tablename__ = "recipe_download_history"

    id = Column(Integer, primary_key=True)
    plc_name = Column(Text, nullable=False)
    recipe_code = Column(Text, nullable=False)
    recipe_version = Column(Integer, nullable=False)
    download_status = Column(Text, nullable=False)
    downloaded_by = Column(Text)
    download_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    download_start_time = Column(DateTime)
    download_end_time = Column(DateTime)
    download_message = Column(Text)


class RecipeUploadHistory(Base, DictMixin):

    __tablename__ = "recipe_upload_history"

    id = Column(Integer, primary_key=True)
    plc_name = Column(Text)
    recipe_code = Column(Text)
    recipe_version = Column(Integer)
    uploaded_by = Column(Text)
    uploaded_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    status = Column(Text)
    remarks = Column(Text)


class PLCRegistry(Base, DictMixin):

    __tablename__ = "plc_registry"

    id = Column(Integer, primary_key=True)
    machine_stage_id = Column(Integer, nullable=False)
    plc_name = Column(Text, nullable=False)
    ip_address = Column(Text, nullable=False)
    controller_type = Column(Text)
    firmware_revision = Column(Text)
    program_revision = Column(Text)
    description = Column(Text)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    processor_name = Column(Text)
    plc_software = Column(Text)
    last_verified_at = Column(DateTime)
    created_by = Column(Text)
    actual_processor_name = Column(Text)
    actual_firmware_revision = Column(Text)
    actual_serial_number = Column(Text)
    actual_program_name = Column(Text)
    verification_status = Column(Text)


class PLCTag(Base, DictMixin):

    __tablename__ = "plc_tags"

    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    stage_id = Column(Integer, nullable=False)
    tag_name = Column(Text, nullable=False)
    tag_type = Column(Text)
    is_array = Column(Integer, server_default=text("0"))
    array_size = Column(Integer)
    array_start_index = Column(Integer)
    array_end_index = Column(Integer)
    description = Column(Text)
    created_by = Column(Text)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    tag_purpose = Column(Text)


class PLCOperationJob(Base, DictMixin):

    __tablename__ = "plc_operation_jobs"

    id = Column(String, primary_key=True)
    recipe_id = Column(Integer)
    plc_id = Column(Integer)
    operation = Column(Text)
    title = Column(Text)
    status = Column(Text)
    success = Column(Integer)
    progress_percent = Column(Integer)
    current_step = Column(Text)
    started_by = Column(Text)
    user_role = Column(Text)
    result_json = Column(Text)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    completed_at = Column(DateTime)


class AuditLog(Base, DictMixin):

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    username = Column(Text)
    role = Column(Text)
    workstation_name = Column(Text)
    client_ip = Column(Text)
    plc_name = Column(Text)
    recipe_code = Column(Text)
    recipe_version = Column(Integer)
    record_id = Column(Integer)
    parameter_name = Column(Text)
    old_value = Column(Text)
    new_value = Column(Text)
    action = Column(Text)
    change_source = Column(Text)
    reason = Column(Text)


class User(Base, DictMixin):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    last_login = Column(DateTime)
    created_by = Column(Text)


class UserSession(Base, DictMixin):

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    username = Column(Text)
    login_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    logout_time = Column(DateTime)
    client_ip = Column(Text)
    workstation_name = Column(Text)


class PhaseControlMaster(Base, DictMixin):

    __tablename__ = "phase_control_master"

    id = Column(Integer, primary_key=True)
    stage_type = Column(Text, nullable=False)
    phase_control_name = Column(Text, nullable=False)
    description = Column(Text)
    display_order = Column(Integer, server_default=text("0"))
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class PhaseControlOption(Base, DictMixin):

    __tablename__ = "phase_control_options"

    id = Column(Integer, primary_key=True)
    phase_control_id = Column(Integer, nullable=False)
    option_code = Column(Text, nullable=False)
    description = Column(Text)
    display_order = Column(Integer, server_default=text("0"))
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class PhaseControlMapping(Base, DictMixin):

    __tablename__ = "phase_control_mapping"

    id = Column(Integer, primary_key=True)
    machine_stage_id = Column(Integer, nullable=False)
    phase_control_id = Column(Integer, nullable=False)
    plc_tag = Column(Text, nullable=False)
    array_index = Column(Integer)
    plc_data_type = Column(Text, nullable=False)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class TemplateMaster(Base, DictMixin):

    __tablename__ = "template_master"

    id = Column(Integer, primary_key=True)
    machine_stage_id = Column(Integer, nullable=False)
    template_name = Column(Text, nullable=False)
    template_version = Column(Integer, server_default=text("1"))
    description = Column(Text)
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class TemplateParameter(Base, DictMixin):

    __tablename__ = "template_parameters"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, nullable=False)
    parameter_name = Column(Text, nullable=False)
    parameter_description = Column(Text)
    plc_tag = Column(Text, nullable=False)
    array_index = Column(Integer)
    data_type = Column(Text, nullable=False)
    engineering_unit_id = Column(Integer)
    minimum_value = Column(Text)
    maximum_value = Column(Text)
    default_value = Column(Text, server_default=text("'0'"))
    required_flag = Column(Integer, server_default=text("1"))
    validation_required = Column(Integer, server_default=text("1"))
    critical_parameter = Column(Integer, server_default=text("0"))
    change_reason_required = Column(Integer, server_default=text("0"))
    display_order = Column(Integer, server_default=text("0"))
    active = Column(Integer, server_default=text("1"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
