# Unraid RRDTool Monitoring System

A Docker-based sensor monitoring system for Unraid servers using [RRDtool](https://oss.oetiker.ch/rrdtool/), the industry-standard data logging and graphing system. RRDtool has been the backbone of monitoring solutions for decades, powering everything from Nagios to enterprise network monitoring.

## Overview

This system collects and visualizes system metrics from your Unraid server:
- **System sensors**: CPU temperatures, motherboard temperatures, fan speeds (via Linux hwmon)
- **Disk temperatures**: Individual disk monitoring using Unraid's disk information
- **Historical graphs**: Automated PNG graph generation with multiple time ranges

Built on a multi-config architecture where each sensor group (system, disks, etc.) has its own configuration file, RRD database, and graph outputs. All collection and graphing runs automatically via cron inside a Docker container.

## Example Graphs

### System Temperatures (Dark Theme)
![System CPU Temperatures - Day View](images/system_cpu_temps_day.png)
*Dark theme with high contrast - ideal for standalone displays*

### Disk Temperatures (Light Theme)
![Disk Temperatures - Day View](images/disks_temps_day.png)
*Light theme matching Unraid web GUI - seamless dashboard integration*

## Features

- **Built-in web server**: View all graphs in your browser at `http://your-server:8080`
- **Theme system**: Light and dark themes with customizable colors and fonts
  - `unraid-light` - Matches Unraid web GUI for seamless dashboard integration
  - `unraid-dark` - High contrast dark theme for standalone displays
  - Support for custom themes with named colors and alpha transparency
- **Multi-config system**: Monitor different sensor groups independently
- **Flexible sensor sources**:
  - Linux hwmon (`sysfs`) for hardware sensors
  - Unraid disk database for disk temperatures
- **Smart hwmon resolution**: Uses chip names instead of unreliable hwmon indices
- **Automated collection**: Runs every minute via cron
- **Automated graphing**: Generates fresh graphs every 15 minutes
- **Configurable time ranges**: 12-hour, day, week, or custom periods
- **Transform expressions**: Apply scaling/calculations to raw sensor values
- **Designed for maintainability**: Clean Python code, JSON configs, LLM-friendly architecture

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mattjoyce/unraid-rrdtool.git
   cd unraid-rrdtool
   ```

2. **Configure your sensors**:
   Edit `config/system.json` and `config/disk.json` to match your hardware

3. **Build and run**:
   ```bash
   docker build -t rrdtool-graphs:latest .
   docker run -d --name rrdtool-graphs --restart unless-stopped \
     -e TZ=Australia/Sydney \
     -p 8080:8080 \
     -v "$PWD/config:/config" \
     -v "$PWD/data:/data" \
     --mount type=bind,source=/sys,target=/hostsys,readonly \
     -v /var/local/emhttp:/var/local/emhttp:ro \
     rrdtool-graphs:latest
   ```

4. **View graphs**:
   - Web interface: Open `http://your-server-ip:8080` in your browser
   - Direct files: Graphs are also available in `./data/graphs/` directory

## Configuration

Each `config/*.json` file defines an independent monitoring group. See [CLAUDE.md](CLAUDE.md) for detailed configuration schema and architecture documentation.

### Themes

Select a theme for each config to control graph appearance:

```json
{
  "schema_version": 2,
  "enabled": true,
  "theme": "unraid-light",
  "prefix": "system",
  ...
}
```

Themes are stored in `config/themes/*.json` and control colors, fonts, and visual styling. Create custom themes by copying and modifying existing ones.

### Example sensor configuration:
```json
{
  "id": "cpu_temp",
  "name": "CPU Temperature",
  "unit": "°C",
  "path": "/hostsys/{k10temp}/temp1_input",
  "transform": "value / 1000",
  "min": 0,
  "max": 150
}
```

The `{k10temp}` placeholder automatically resolves to the correct hwmon device path, even after reboots.

## Project Structure

```
├── config/              # JSON configuration files
│   ├── system.json     # System sensors (CPU, motherboard, fans)
│   ├── disk.json       # Disk temperature monitoring
│   └── themes/         # Graph theme files
│       ├── unraid-light.json
│       └── unraid-dark.json
├── theme_loader.py     # Theme loading and color resolution
├── data/               # RRD databases and generated graphs
├── Dockerfile          # Container definition
└── CLAUDE.md          # Detailed architecture and development docs
```

## Credits

Built with [RRDtool](https://oss.oetiker.ch/rrdtool/) by Tobi Oetiker - a time-tested, rock-solid data logging and graphing system that's been the foundation of monitoring solutions since the late 1990s. From Nagios deployments to enterprise network operations, RRDtool just works.

## Documentation

- [CLAUDE.md](CLAUDE.md) - Complete architecture, configuration schema, and development guide
- [info.md](info.md) - Additional project information

## License

See LICENSE file for details.
