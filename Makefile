.PHONY: install dev sim sim-all mocks test lint clean replay

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

sim:
	python -m netops_sim.runner mtu_mismatch

sim-all:
	python -m netops_sim.runner mtu_mismatch
	python -m netops_sim.runner bgp_flap
	python -m netops_sim.runner silent_packet_loss
	python -m netops_sim.runner tep_ip_collision
	python -m netops_sim.runner dfw_rule_break
	python -m netops_sim.runner pnic_failure_vmotion

mocks:
	@echo "Starting mock APIs on:"
	@echo "  NSX Policy API   → http://localhost:8443"
	@echo "  Cisco NX-API     → http://localhost:8444"
	@echo "  gNMI WebSocket   → ws://localhost:8445/gnmi/subscribe"
	python -m netops_sim.emitters.serve_all

test:
	pytest -xvs tests/

lint:
	ruff check netops_sim tests
	ruff format --check netops_sim tests

format:
	ruff format netops_sim tests

clean:
	rm -rf runs/*.jsonl runs/*.truth.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

replay:
	@echo "Usage: python -m netops_sim.replay runs/<file>.jsonl --speed 10"
