# Changelog

## [1.0.0] - 2024-02-23

### Added
- Initial open-source release 🐱
- System collector: CPU, memory, swap, disk, network I/O, load average
- Process collector: count, CPU %, memory; `critical` flag for always-page processes
- HTTP collector: status code, response time, body regex; per-check severity
- Log collector: regex matching, tail tracking, log rotation handling
- Two-tier alert routing: paging (PagerDuty, OpsGenie) vs non-paging (Slack, Datadog)
- Alert deduplication and configurable cooldown (default 5 min)
- Auto-resolve notifications
- InfluxDB, StatsD, and stdout telemetry sinks
- YAML config with deep-merge defaults
- Auto config file discovery
- `lurkkit --init`, `--status`, `--validate` CLI commands
- systemd install script
- Extension API: BaseCollector and BaseAlerter for custom plugins
- 14 unit tests
