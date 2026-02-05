# System Maintenance Scripts 🔧

## Operational Maintenance and Setup Tools

Scripts for system maintenance, configuration, and component management.

---

## 🗄️ Database Maintenance

### `setup-postgresql.sh`
- **Purpose**: PostgreSQL database configuration and setup
- **Usage**: Configure database users, permissions, and settings
- **When**: Database reconfiguration or troubleshooting

### `fix-database.sh`  
- **Purpose**: Database repair and optimization
- **Usage**: Repair database issues and optimize performance
- **When**: Database connectivity problems or performance issues

---

## 🎛️ Service Configuration

### `setup-gunicorn-service.sh`
- **Purpose**: Gunicorn WSGI server configuration
- **Usage**: Configure Django application server
- **When**: Service reconfiguration or performance tuning

### Various `setup-*.sh` scripts
- **Purpose**: Component-specific setup and configuration
- **Coverage**: Individual system components
- **When**: Specific component issues or reconfigurations

---

## 🔐 System Security

### `fix-permissions.sh`
- **Purpose**: File and directory permission corrections  
- **Usage**: Restore proper system permissions
- **When**: Permission-related access issues

### `fix-dependencies.sh`
- **Purpose**: Package and library dependency resolution
- **Usage**: Install missing packages and resolve conflicts
- **When**: Dependency errors or package issues

---

## ⚙️ Usage Guidelines

### Safety First
- 🔴 **Always backup** before running maintenance scripts
- 🔴 **Test in non-production** when possible  
- 🔴 **Document changes** for rollback if needed

### Execution Order
1. **Diagnose**: Identify specific issue
2. **Backup**: Create system backup
3. **Execute**: Run appropriate maintenance script
4. **Verify**: Test functionality after changes

### When to Use
- 🔧 Component configuration changes needed
- 🐛 Specific service issues identified
- 📦 Package dependency problems
- 🔒 Permission-related access problems

---

## 🚨 Production Notes

**Current Status**: System is fully operational  
**Recommendation**: Use these scripts only when specific issues are identified  
**Alternative**: For general issues, use scripts in `/active/` directory first

### Maintenance Schedule
- **Regular**: Monthly permission and dependency checks
- **As-needed**: Component-specific reconfigurations  
- **Emergency**: Database repair during issues

---

## 📋 Script Categories

| Category | Scripts | Purpose |
|----------|---------|---------|
| **Database** | setup-postgresql.sh, fix-database.sh | Database management |
| **Services** | setup-gunicorn-service.sh, setup-*.sh | Service configuration |
| **System** | fix-permissions.sh, fix-dependencies.sh | System maintenance |

**Note**: For routine operations, prefer the scripts in `/active/` directory.