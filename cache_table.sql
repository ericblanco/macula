CREATE TABLE cache (
    id bigint NOT NULL,
    ioc character varying(1024) NOT NULL,
    created_ts timestamp with time zone NOT NULL,
    score jsonb NOT NULL
);

CREATE SEQUENCE public.cache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE INDEX idx_cache_ioc ON cache USING btree (ioc);
CREATE INDEX idx_cache_created_ts ON cache USING btree (created_ts);
ALTER TABLE cache ADD CONSTRAINT uq_cache_ioc UNIQUE (ioc);
