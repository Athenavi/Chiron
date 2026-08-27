create table alembic_version
(
    version_num varchar(32) not null
        constraint alembic_version_pkc
            primary key
);

create table admin_api_keys
(
    id             varchar(36) not null
        primary key,
    key_hash       varchar(64)
        unique,
    name           varchar(100),
    tenant_id      varchar(50),
    user_id        varchar(50),
    monthly_quota  integer,
    used_count     bigint,
    used_credits   bigint,
    status         varchar(20),
    expires_at     varchar(255),
    created_at     varchar(255),
    updated_at     varchar(255),
    created_by     varchar(50),
    description    text,
    allowed_models varchar(255),
    rate_limit_qps integer
);

create table admin_cron_jobs
(
    id              varchar(36) not null
        primary key,
    job_id          varchar(50)
        unique,
    name            varchar(100),
    schedule        varchar(50),
    last_run_at     varchar(255),
    last_run_status varchar(20),
    last_error      text,
    next_run_at     varchar(255),
    enabled         boolean,
    metadata_data   json,
    created_at      varchar(255),
    updated_at      varchar(255)
);

create table admin_database_backups
(
    id               varchar(36) not null
        primary key,
    backup_type      varchar(20),
    description      text,
    file_path        varchar(500),
    file_size_mb     varchar(255),
    status           varchar(20),
    error_message    text,
    started_at       varchar(255),
    completed_at     varchar(255),
    duration_seconds integer,
    created_by       varchar(50)
);

create table admin_db_configs
(
    id                   varchar(36) not null
        primary key,
    dsn                  varchar(500),
    host                 varchar(100),
    port                 integer,
    dbname               varchar(100),
    max_open_connections integer,
    max_idle_connections integer,
    conn_max_lifetime    varchar(255),
    status               varchar(20),
    last_health_check    varchar(255),
    avg_query_time_ms    varchar(255),
    database_size_mb     varchar(255),
    total_tables         integer,
    sequential_scans     bigint,
    created_at           varchar(255),
    updated_at           varchar(255)
);

create table admin_model_configs
(
    id                 varchar(36) not null
        primary key,
    model_id           varchar(50)
        unique,
    display_name       varchar(100),
    provider           varchar(50),
    priority           integer,
    weight             integer,
    fallback_chain     varchar(255),
    max_rpm            integer,
    max_tpm            integer,
    concurrent_limit   integer,
    status             varchar(20),
    is_default         boolean,
    input_cost_per_1m  varchar(255),
    output_cost_per_1m varchar(255),
    config_json        json,
    created_at         varchar(255),
    updated_at         varchar(255)
);

create table admin_redis_configs
(
    id                   varchar(36) not null
        primary key,
    host                 varchar(100),
    port                 integer,
    password_hash        varchar(256),
    db_index             integer,
    pool_size            integer,
    min_idle_connections integer,
    max_conn_age         varchar(255),
    status               varchar(20),
    last_health_check    varchar(255),
    avg_latency_ms       varchar(255),
    memory_used_mb       varchar(255),
    connected_clients    integer,
    hits                 bigint,
    misses               bigint,
    created_at           varchar(255),
    updated_at           varchar(255)
);

create table admin_tenants
(
    id                      varchar(36) not null
        primary key,
    tenant_id               varchar(50)
        unique,
    name                    varchar(100),
    company_name            varchar(200),
    contact_email           varchar(100),
    contact_phone           varchar(20),
    max_api_keys            integer,
    max_models              integer,
    monthly_quota           bigint,
    max_concurrent_sessions integer,
    status                  varchar(20),
    expires_at              varchar(255),
    created_at              varchar(255),
    updated_at              varchar(255),
    created_by              varchar(50),
    features                json
);

create table admin_workflow_executions
(
    id               varchar(36) not null
        primary key,
    workflow_id      varchar(50),
    workflow_version integer,
    status           varchar(20),
    started_at       varchar(255),
    completed_at     varchar(255),
    duration_ms      integer,
    input_data       json,
    output_data      json,
    error_message    text,
    triggered_by     varchar(50),
    node_results     json
);

create table admin_workflows
(
    id                      varchar(36) not null
        primary key,
    workflow_id             varchar(50)
        unique,
    name                    varchar(100),
    description             text,
    nodes                   json,
    edges                   json,
    error_handling_strategy varchar(20),
    timeout_ms              integer,
    max_retries             integer,
    version                 integer,
    published_version       integer,
    status                  varchar(20),
    created_by              varchar(50),
    created_at              varchar(255),
    updated_at              varchar(255),
    published_at            varchar(255)
);

create table agent_registry
(
    agent_type  varchar(32) not null
        primary key,
    name        varchar(128),
    description text        not null,
    enabled     boolean,
    config      json,
    created_at  varchar(255)
);

create table conversation_shares
(
    id          varchar(32) not null
        primary key,
    session_id  varchar(128),
    user_id     varchar(36),
    title       varchar(255),
    message_ids varchar(255),
    created_at  varchar(255),
    revoked_at  varchar(255)
);

create table cron_jobs
(
    id            varchar(36) not null
        primary key,
    name          varchar(128),
    schedule      varchar(64),
    task          varchar(255),
    enabled       boolean,
    last_run_at   varchar(255),
    last_status   varchar(16),
    created_at    varchar(255),
    updated_at    varchar(255),
    tenant_id     varchar(36),
    user_id       varchar(36),
    webhook_token varchar(64)
);

create table ent_catalog_installs
(
    item_id      varchar(36) not null,
    tenant_id    varchar(36) not null,
    enabled      boolean,
    installed_at varchar(255),
    primary key (item_id, tenant_id)
);

create table ent_catalog_items
(
    id         varchar(36) not null
        primary key,
    type       varchar(8),
    name       varchar(128),
    version    varchar(32),
    manifest   json,
    status     varchar(16),
    created_by varchar(36),
    created_at varchar(255),
    updated_at varchar(255)
);

create table ent_group_members
(
    group_id varchar(36) not null,
    user_id  varchar(36) not null,
    primary key (group_id, user_id)
);

create table ent_group_roles
(
    group_id varchar(36) not null,
    role_id  varchar(36) not null,
    primary key (group_id, role_id)
);

create table ent_templates
(
    id          varchar(36) not null
        primary key,
    type        varchar(16),
    name        varchar(128),
    description text        not null,
    payload     json,
    published   boolean,
    created_at  varchar(255),
    updated_at  varchar(255)
);

create table ent_tenant_policies
(
    tenant_id           varchar(36) not null
        primary key,
    privacy_mode        boolean,
    data_retention_days integer,
    training_allowed    boolean,
    redaction_rules     json,
    updated_at          varchar(255)
);

create table ent_user_roles
(
    user_id varchar(36) not null,
    role_id varchar(36) not null,
    primary key (user_id, role_id)
);

create table guest_storage
(
    client_id  varchar(64) not null
        primary key,
    storage_id varchar(64)
        unique,
    created_at varchar(255)
);

create table llm_models
(
    id             varchar(36) not null
        primary key,
    provider       varchar(32),
    name           varchar(128),
    display_name   varchar(128),
    enabled        boolean,
    context_window integer,
    created_at     varchar(255),
    updated_at     varchar(255)
);

create table memory_summaries
(
    id               varchar(64) not null
        primary key,
    tenant_id        varchar(64),
    user_id          varchar(64),
    session_id       varchar(64),
    content          text        not null,
    topics           json,
    entities         json,
    turn_start       integer,
    turn_end         integer,
    content_hash     varchar(80),
    access_count     integer,
    last_accessed_at varchar(255),
    status           varchar(16),
    created_at       varchar(255)
);

create table payments
(
    id                varchar(64) not null
        primary key,
    user_id           varchar(32),
    channel           varchar(16),
    credits           integer,
    amount_cents      bigint,
    currency          varchar(8),
    status            varchar(16),
    qr_code           text,
    provider_order_id varchar(64),
    trade_no          varchar(64),
    created_at        varchar(255),
    paid_at           varchar(255),
    expired_at        varchar(255)
);

create table schema_migrations
(
    version    bigserial
        primary key,
    name       varchar(255),
    checksum   varchar(128),
    applied_at varchar(255)
);

create table stripe_payments
(
    session_id   varchar(128) not null
        primary key,
    user_id      varchar(36),
    credits      integer,
    amount_cents bigint,
    status       varchar(16),
    created_at   varchar(255),
    completed_at varchar(255)
);

create table system_settings
(
    id         serial
        primary key,
    category   varchar(32),
    key        varchar(64),
    value      json,
    updated_at varchar(255),
    updated_by varchar(36),
    encrypted  boolean
);

create table tenants
(
    id         varchar(36) not null
        primary key,
    name       varchar(255),
    created_at varchar(255),
    status     varchar(16)
);

create table tool_calls
(
    id          varchar(36) not null
        primary key,
    session_id  varchar(36),
    message_id  varchar(36),
    tool_name   varchar(128),
    input       json,
    output      text        not null,
    is_error    boolean,
    duration_ms bigint,
    created_at  varchar(255)
);

create table unified_sessions
(
    id             varchar(36) not null
        primary key,
    tenant_id      varchar(36),
    user_id        varchar(36),
    title          varchar(255),
    mode           varchar(16),
    shared_context json,
    created_at     varchar(255),
    updated_at     varchar(255)
);

create table user_memory_profile
(
    tenant_id          varchar(64)  not null,
    user_id            varchar(64)  not null,
    slot               varchar(32)  not null,
    item_key           varchar(128) not null,
    item_value         json,
    confidence         integer,
    source             varchar(16),
    version            integer,
    confirmed_at       varchar(255),
    last_referenced_at varchar(255),
    created_at         varchar(255),
    updated_at         varchar(255),
    primary key (tenant_id, user_id, slot, item_key)
);

create table workflow_instances
(
    id            varchar(64) not null
        primary key,
    user_id       varchar(64),
    workflow_id   varchar(64),
    workflow_name varchar(255),
    status        varchar(16),
    results       json,
    error         text,
    created_at    varchar(255),
    updated_at    varchar(255)
);

create table admin_api_call_logs
(
    id                  varchar(36) not null
        primary key,
    api_key_id          varchar(36)
        references admin_api_keys,
    model_id            varchar(50),
    workflow_id         varchar(50),
    endpoint            varchar(100),
    method              varchar(10),
    request_size_bytes  integer,
    response_size_bytes integer,
    duration_ms         integer,
    status_code         integer,
    retry_count         integer,
    input_tokens        integer,
    output_tokens       integer,
    credits_consumed    bigint,
    created_at          varchar(255)
);

create table admin_domains
(
    id             varchar(36) not null
        primary key,
    domain         varchar(100)
        unique,
    tenant_id      varchar(50)
        references admin_tenants (tenant_id),
    dns_provider   varchar(50),
    dns_record_id  varchar(100),
    cname_target   varchar(200),
    ssl_status     varchar(20),
    ssl_expires_at varchar(255),
    auto_renew     boolean,
    status         varchar(20),
    verified_at    varchar(255),
    verified_by    varchar(50),
    created_at     varchar(255),
    updated_at     varchar(255)
);

create table admin_tenant_usage
(
    id               varchar(36) not null
        primary key,
    tenant_id        varchar(50)
        references admin_tenants (tenant_id),
    stat_date        varchar(255),
    api_calls        bigint,
    tokens_used      bigint,
    credits_consumed bigint,
    storage_mb       varchar(255),
    created_at       varchar(255)
);

create table agents
(
    id              varchar(36) not null
        primary key,
    tenant_id       varchar(36)
        references tenants,
    name            varchar(255),
    description     text,
    system_prompt   text,
    tools           json,
    llm_config      json,
    max_turns       integer,
    timeout_seconds integer,
    enabled         boolean,
    created_at      varchar(255),
    updated_at      varchar(255),
    user_id         varchar(36),
    visibility      varchar(16)
);

create table domains
(
    id         varchar(36) not null
        primary key,
    tenant_id  varchar(36)
        references tenants,
    domain     varchar(255)
        unique,
    ssl_status varchar(16),
    verified   boolean,
    created_at varchar(255),
    updated_at varchar(255)
);

create table ent_captcha_config
(
    id         varchar(36) not null
        primary key,
    tenant_id  varchar(36)
        references tenants,
    provider   varchar(32),
    site_key   varchar(256),
    secret_enc text        not null,
    verify_url varchar(512),
    enabled    boolean,
    created_at varchar(255),
    updated_at varchar(255)
);

create table ent_groups
(
    id          varchar(36) not null
        primary key,
    tenant_id   varchar(36)
        references tenants,
    name        varchar(128),
    description text,
    created_at  varchar(255)
);

create table ent_oidc_providers
(
    id                varchar(36) not null
        primary key,
    tenant_id         varchar(36)
        references tenants,
    name              varchar(64),
    issuer            varchar(512),
    client_id         varchar(256),
    client_secret_enc text        not null,
    scopes            varchar(255),
    enabled           boolean,
    auto_provision    boolean,
    role_mapping      json,
    created_at        varchar(255),
    updated_at        varchar(255),
    protocol          varchar(16),
    provider_type     varchar(32),
    display_name      varchar(64),
    icon              varchar(64),
    sort_order        integer,
    auth_url          varchar(512),
    token_url         varchar(512),
    userinfo_url      varchar(512),
    extra             json
);

create table ent_quota_pools
(
    id            varchar(36) not null
        primary key,
    tenant_id     varchar(36)
        references tenants,
    resource_type varchar(20),
    total_amount  bigint,
    period        varchar(10),
    created_at    varchar(255),
    updated_at    varchar(255)
);

create table ent_roles
(
    id           varchar(36) not null
        primary key,
    tenant_id    varchar(36)
        references tenants,
    name         varchar(64),
    display_name varchar(128),
    is_builtin   boolean,
    permissions  varchar(255),
    created_at   varchar(255),
    updated_at   varchar(255)
);

create table enterprise_tasks
(
    id          varchar(36) not null
        primary key,
    tenant_id   varchar(36)
        references tenants,
    user_id     varchar(32),
    title       varchar(255),
    description text        not null,
    project     varchar(128),
    assignee    varchar(128),
    priority    varchar(16),
    status      varchar(16),
    created_at  varchar(255),
    updated_at  varchar(255)
);

create table kb_articles
(
    id         varchar(36) not null
        primary key,
    tenant_id  varchar(36)
        references tenants,
    user_id    varchar(32),
    title      varchar(255),
    content    text        not null,
    tags       varchar(255),
    category   varchar(64),
    created_at varchar(255),
    updated_at varchar(255)
);

create table marketing_campaigns
(
    id            varchar(36) not null
        primary key,
    tenant_id     varchar(36)
        references tenants,
    user_id       varchar(32),
    name          varchar(255),
    description   text        not null,
    campaign_type varchar(32),
    config        json,
    status        varchar(16),
    created_at    varchar(255),
    updated_at    varchar(255)
);

create table media_assets
(
    id            varchar(36) not null
        primary key,
    tenant_id     varchar(36)
        references tenants,
    user_id       varchar(36),
    type          varchar(16),
    name          varchar(255),
    file_url      varchar(1024),
    file_path     varchar(512),
    mime_type     varchar(64),
    thumbnail     varchar(512),
    metadata_data json,
    tags          varchar(255),
    category      varchar(64),
    size          bigint,
    created_at    timestamp,
    updated_at    timestamp,
    parent_id     varchar(64)
);

create table meeting_notes
(
    id           varchar(36) not null
        primary key,
    tenant_id    varchar(36)
        references tenants,
    user_id      varchar(32),
    title        varchar(255),
    notes        text        not null,
    summary      text,
    participants varchar(255),
    date         varchar(255),
    created_at   varchar(255)
);

create table okrs
(
    id          varchar(36) not null
        primary key,
    tenant_id   varchar(36)
        references tenants,
    user_id     varchar(32),
    objective   varchar(255),
    key_results json,
    quarter     varchar(16),
    status      varchar(16),
    created_at  varchar(255),
    updated_at  varchar(255)
);

create table support_tickets
(
    id          varchar(36) not null
        primary key,
    tenant_id   varchar(36)
        references tenants,
    user_id     varchar(32),
    subject     varchar(255),
    description text        not null,
    priority    varchar(16),
    status      varchar(16),
    assignee    varchar(128),
    created_at  varchar(255),
    updated_at  varchar(255)
);

create table unified_messages
(
    id            serial
        primary key,
    session_id    varchar(36)
        references unified_sessions,
    role          varchar(16),
    content       text not null,
    metadata_data json,
    error         text not null,
    created_at    varchar(255)
);

create table uploads
(
    id              varchar(64) not null
        primary key,
    user_id         varchar(64),
    name            varchar(255),
    size            bigint,
    mime_type       varchar(64),
    purpose         varchar(16),
    parent_id       varchar(64),
    category        varchar(64),
    chunk_size      integer,
    chunk_count     integer,
    chunks_received text,
    status          varchar(16),
    created_at      varchar(255),
    updated_at      varchar(255),
    tenant_id       varchar(36)
        references tenants
);

create table users
(
    id            varchar(36) not null
        primary key,
    tenant_id     varchar(36)
        references tenants,
    email         varchar(255),
    name          varchar(128),
    password_hash varchar(255),
    role          varchar(16),
    storage_id    varchar(64)
        unique,
    credits       integer,
    created_at    varchar(255),
    updated_at    varchar(255),
    phone         varchar(32),
    password_set  boolean,
    settings      json
);

create table wiki_pages
(
    id         varchar(36) not null
        primary key,
    tenant_id  varchar(36)
        references tenants,
    user_id    varchar(32),
    title      varchar(255),
    content    text        not null,
    tags       varchar(255),
    created_at varchar(255),
    updated_at varchar(255)
);

create table agent_sessions
(
    id         varchar(128) not null
        primary key,
    user_id    varchar(36)
        references users,
    agent_id   varchar(36)
        references agents,
    name       varchar(128),
    task       text         not null,
    status     varchar(16),
    result     text,
    created_at varchar(255),
    updated_at varchar(255),
    tenant_id  varchar(36)
        references tenants
);

create table api_keys
(
    id           varchar(36) not null
        primary key,
    user_id      varchar(36)
        references users,
    name         varchar(128),
    key_hash     varchar(64),
    last_used_at varchar(255),
    expires_at   varchar(255),
    created_at   varchar(255),
    revoked      boolean
);

create table audit_logs
(
    id            varchar(36) not null
        primary key,
    tenant_id     varchar(36)
        references tenants,
    user_id       varchar(36)
        references users,
    action        varchar(64),
    resource_type varchar(64),
    resource_id   varchar(64),
    details       json,
    ip_address    varchar(45),
    created_at    varchar(255)
);

create table credit_transactions
(
    id         varchar(36) not null
        primary key,
    user_id    varchar(36)
        references users,
    amount     integer,
    balance    integer,
    reason     varchar(64),
    created_at varchar(255)
);

create table ent_model_policies
(
    id               varchar(36) not null
        primary key,
    tenant_id        varchar(36)
        references tenants,
    role_id          varchar(36)
        references ent_roles,
    allowed_models   varchar(255),
    per_model_limits json,
    created_at       varchar(255),
    updated_at       varchar(255)
);

create table ent_quota_allocations
(
    id          varchar(36) not null
        primary key,
    pool_id     varchar(36)
        references ent_quota_pools,
    target_type varchar(10),
    target_id   varchar(36),
    amount      bigint,
    created_at  varchar(255)
);

create table ent_user_identities
(
    id          varchar(36) not null
        primary key,
    user_id     varchar(36)
        references users,
    provider_id varchar(36)
        references ent_oidc_providers,
    subject     varchar(256),
    email       varchar(255),
    created_at  varchar(255)
);

create table knowledge_bases
(
    id               varchar(36) not null
        primary key,
    tenant_id        varchar(36)
        references tenants,
    user_id          varchar(36)
        references users,
    name             varchar(255),
    description      text,
    type             varchar(32),
    visibility       varchar(32),
    status           varchar(32),
    document_count   integer,
    total_size_bytes bigint,
    credits_consumed integer,
    config           json,
    created_at       varchar(255),
    updated_at       varchar(255),
    doc_count        integer
);

create table sessions
(
    id         varchar(36) not null
        primary key,
    tenant_id  varchar(36)
        references tenants,
    user_id    varchar(36)
        references users,
    agent_id   varchar(36)
        references agents,
    title      varchar(255),
    status     varchar(16),
    created_at varchar(255),
    updated_at varchar(255),
    pinned     boolean
);

create table tasks
(
    id          varchar(36) not null
        primary key,
    user_id     varchar(36)
        references users,
    type        varchar(32),
    status      varchar(16),
    priority    integer,
    payload     json,
    result      json,
    error       text,
    retries     integer,
    max_retries integer,
    created_at  varchar(255),
    updated_at  varchar(255)
);

create table workflow_graphs
(
    id         varchar(32) not null
        primary key,
    name       varchar(255),
    user_id    varchar(36)
        references users,
    graph_json json,
    created_at varchar(255),
    updated_at varchar(255)
);

create table billing_records
(
    id            varchar(36) not null
        primary key,
    tenant_id     varchar(36)
        references tenants,
    user_id       varchar(36)
        references users,
    session_id    varchar(36)
        references sessions,
    input_tokens  bigint,
    output_tokens bigint,
    cost_cents    integer,
    created_at    varchar(255),
    group_id      varchar(36)
);

create table knowledge_documents
(
    id                varchar(36) not null
        primary key,
    knowledge_base_id varchar(36)
        references knowledge_bases,
    tenant_id         varchar(36)
        references tenants,
    user_id           varchar(36)
        references users,
    name              varchar(255),
    file_url          varchar(1024),
    file_type         varchar(32),
    file_size_bytes   bigint,
    chunk_count       integer,
    status            varchar(32),
    error_message     text,
    metadata_data     json,
    created_at        varchar(255),
    updated_at        varchar(255),
    content           varchar(255)
);

create table messages
(
    id         varchar(36) not null
        primary key,
    session_id varchar(36)
        references sessions,
    role       varchar(16),
    content    text        not null,
    tool_calls json,
    created_at varchar(255)
);

create table knowledge_chunks
(
    id                varchar(36) not null
        primary key,
    document_id       varchar(36)
        references knowledge_documents,
    knowledge_base_id varchar(36)
        references knowledge_bases,
    tenant_id         varchar(36)
        references tenants,
    chunk_index       integer,
    content           text        not null,
    metadata_data     json,
    search_vector     varchar(255),
    created_at        varchar(255)
);

