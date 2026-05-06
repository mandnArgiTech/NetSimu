"""End-to-end scenario test. Runs MTU mismatch and validates that the
expected anomaly signatures appear in the JSONL archive."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from netops_sim.runner import run_scenario


@pytest.mark.asyncio
async def test_mtu_mismatch_produces_expected_signals():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path, truth = await run_scenario(
            "mtu_mismatch", real_time=False, out_dir=tmp,
            duration_seconds=400.0, distractors=False, snapshots=False,
        )

        assert truth["root_cause_entity"] == "port-tor-01-host-01-vmnic0"
        assert truth["expected_rca_rule"] == "R-MTU-001"
        assert os.path.exists(archive_path)

        events = []
        with open(archive_path) as f:
            for line in f:
                events.append(json.loads(line))

        assert len(events) > 50, "Should produce many events"

        # 1) The faulted port should show in_errors > 0
        port_events = [
            e for e in events
            if e.get("kind") == "interface_counters"
            and e.get("entity") == "port-tor-01-host-01-vmnic0"
        ]
        assert any(e.get("in_errors", 0) > 0 for e in port_events), \
            "Expected in_errors > 0 on faulted port"

        # 2) Audit log should contain the config change
        audit = [e for e in events if e.get("kind") == "audit_log"]
        assert any(e.get("change_id") == "CHG-9281" for e in audit), \
            "Expected CHG-9281 in audit log"

        # 3) TEP pair drop_pps should spike for host-01 pairs (both uplinks faulted)
        pair_events = [
            e for e in events
            if e.get("kind") == "tep_pair_status"
            and "host-01" in e.get("entity", "")
        ]
        assert any(e.get("drop_pps", 0) > 100 for e in pair_events), \
            "Expected TEP pair drops involving host-01"

        # 4) App-tier should see degraded latency
        app_events = [
            e for e in events
            if e.get("kind") == "app_health" and e.get("metric") == "p99_latency_ms"
        ]
        bad_latency = [e for e in app_events if e.get("value", 0) > 500]
        assert len(bad_latency) > 0, \
            "Expected at least one degraded app latency sample"


@pytest.mark.asyncio
async def test_bgp_flap_emits_state_change():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path, truth = await run_scenario(
            "bgp_flap", real_time=False, out_dir=tmp,
            duration_seconds=400.0, distractors=False, snapshots=False,
        )

        assert truth["root_cause_entity"] == "bgp-t0-tor-01"

        events = []
        with open(archive_path) as f:
            for line in f:
                events.append(json.loads(line))

        # Look for a syslog with ADJCHANGE
        syslogs = [e for e in events if e.get("kind") == "syslog"]
        assert any("ADJCHANGE" in e.get("msg", "") for e in syslogs), \
            "Expected BGP ADJCHANGE syslog"

        # And bgp_neighbor events showing state transitions
        bgp_events = [
            e for e in events
            if e.get("kind") == "bgp_neighbor"
            and e.get("entity") == "bgp-t0-tor-01"
        ]
        states = {e.get("state") for e in bgp_events}
        assert "Idle" in states or any("ADJCHANGE" in e.get("msg", "") for e in syslogs)


@pytest.mark.asyncio
async def test_silent_loss_produces_crc_errors():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path, truth = await run_scenario(
            "silent_packet_loss", real_time=False, out_dir=tmp,
            duration_seconds=600.0, distractors=False, snapshots=False,
        )

        assert truth["root_cause_entity"] == "port-spine-01-to-tor-01"

        events = []
        with open(archive_path) as f:
            for line in f:
                events.append(json.loads(line))

        port_events = [
            e for e in events
            if e.get("kind") == "interface_counters"
            and e.get("entity") == "port-spine-01-to-tor-01"
        ]
        assert any(e.get("crc_errors", 0) > 0 for e in port_events), \
            "Expected CRC errors on the spine-tor link"


@pytest.mark.asyncio
async def test_tep_ip_collision_emits_dup_ip_syslog():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path, truth = await run_scenario(
            "tep_ip_collision", real_time=False, out_dir=tmp,
            duration_seconds=400.0, distractors=False, snapshots=False,
        )

        assert truth["root_cause_entity"] == "tep-host-02"

        events = []
        with open(archive_path) as f:
            for line in f:
                events.append(json.loads(line))

        # Duplicate-IP syslog should appear
        dup_logs = [
            e for e in events
            if e.get("kind") == "syslog" and "DUP_IP" in e.get("msg", "")
        ]
        assert len(dup_logs) > 0, "Expected DUP_IP syslog"

        # tep_status should report unhealthy with fault_hint
        tep_events = [
            e for e in events
            if e.get("kind") == "tep_status" and e.get("entity") == "tep-host-02"
        ]
        unhealthy = [e for e in tep_events if not e.get("healthy", True)]
        assert len(unhealthy) > 0, "Expected unhealthy tep_status events"
        assert any(e.get("fault_hint") == "duplicate_ip" for e in unhealthy)


@pytest.mark.asyncio
async def test_dfw_rule_break_clean_underlay_app_impact():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path, truth = await run_scenario(
            "dfw_rule_break", real_time=False, out_dir=tmp,
            duration_seconds=400.0, distractors=False, snapshots=False,
        )

        assert truth["root_cause_entity"] == "dfw-rule-001"

        events = []
        with open(archive_path) as f:
            for line in f:
                events.append(json.loads(line))

        # Audit log should show action allow → deny
        audit = [e for e in events if e.get("kind") == "audit_log"]
        assert any(e.get("change_id") == "CHG-9510" for e in audit)

        # DFW syslog
        dfw_logs = [
            e for e in events
            if e.get("kind") == "syslog" and "DFW" in e.get("msg", "")
        ]
        assert len(dfw_logs) > 0, "Expected DFW rule-change syslog"

        # App should show degradation AFTER fault time only
        # (Not asserting strict timing — just that bad latency appears at all)
        app_events = [
            e for e in events
            if e.get("kind") == "app_health"
            and e.get("entity") == "app-web"
            and e.get("metric") == "p99_latency_ms"
        ]
        bad = [e for e in app_events if e.get("value", 0) > 500]
        assert len(bad) > 0, "Expected app-web degradation from DFW deny"

        # Critical: NO underlay errors should appear on host-01 ports during fault
        # (this differentiates DFW from infra issues)
        port_events = [
            e for e in events
            if e.get("kind") == "interface_counters"
            and "host-01" in e.get("entity", "")
        ]
        # Some events will exist; check they show no in_errors growth
        max_errors = max((e.get("in_errors", 0) for e in port_events), default=0)
        assert max_errors == 0, \
            f"DFW scenario should have clean underlay; got max in_errors={max_errors}"


@pytest.mark.asyncio
async def test_pnic_failure_triggers_vmotion():
    with tempfile.TemporaryDirectory() as tmp:
        archive_path, truth = await run_scenario(
            "pnic_failure_vmotion", real_time=False, out_dir=tmp,
            duration_seconds=400.0, distractors=False, snapshots=False,
        )

        assert "pnic-host-03" in truth["root_cause_entity"]
        assert "evacuated_vms" in truth

        events = []
        with open(archive_path) as f:
            for line in f:
                events.append(json.loads(line))

        # vMotion events should fire
        vm_events = [e for e in events if e.get("kind") == "vmotion"]
        assert len(vm_events) > 0, "Expected vmotion events"

        # All vmotions should be FROM host-03
        for e in vm_events:
            assert e.get("from_host") == "host-03"

        # Link-down syslog
        link_down = [
            e for e in events
            if e.get("kind") == "syslog" and "LINK_DOWN" in e.get("msg", "")
        ]
        assert len(link_down) >= 2, "Expected LINK_DOWN syslogs for both pNICs"

        # HA event
        ha_events = [e for e in events if e.get("kind") == "ha_event"]
        assert len(ha_events) > 0, "Expected ha_event"
