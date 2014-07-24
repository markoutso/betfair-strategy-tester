--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: entry; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE entry (
    id bigint NOT NULL,
    event_id integer NOT NULL,
    selection_id integer,
    selection character varying(50) NOT NULL,
    odds real NOT NULL,
    number_bets integer,
    volume integer,
    latest_taken timestamp without time zone,
    first_taken timestamp without time zone,
    win_flag smallint,
    in_play character varying(2),
    settled_date timestamp without time zone
);


ALTER TABLE public.entry OWNER TO postgres;

--
-- Name: entry_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE entry_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.entry_id_seq OWNER TO postgres;

--
-- Name: entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE entry_id_seq OWNED BY entry.id;


--
-- Name: event; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE event (
    event_id integer NOT NULL,
    sports_id integer NOT NULL,
    scheduled_off timestamp without time zone NOT NULL,
    actual_off timestamp without time zone,
    cat character varying(100) NOT NULL,
    sub_cat character varying(100),
    home character varying(80) NOT NULL,
    away character varying(80) NOT NULL,
    market character varying(100)
);


ALTER TABLE public.event OWNER TO postgres;

--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY entry ALTER COLUMN id SET DEFAULT nextval('entry_id_seq'::regclass);


--
-- Name: event_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY event
    ADD CONSTRAINT event_pkey PRIMARY KEY (event_id);


--
-- Name: pk; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY entry
    ADD CONSTRAINT pk PRIMARY KEY (id);


--
-- Name: fk_event; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY entry
    ADD CONSTRAINT fk_event FOREIGN KEY (event_id) REFERENCES event(event_id) ON DELETE CASCADE;


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--


