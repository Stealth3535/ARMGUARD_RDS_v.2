# 🛡️ ArmGuard VPN Security Policy

## Classification: RESTRICTED
**Document Type**: Network Security Compliance Policy  
**System**: ArmGuard Military Inventory Management  
**VPN Technology**: WireGuard with Military-Grade Controls  
**Implementation Status**: ✅ **FULLY COMPLIANT**  
**Last Updated**: February 2026  
**Review Cycle**: Quarterly  

---

## 1. Security Compliance Overview

### 1.1 Network Architecture Compliance
✅ **REQUIREMENT**: Transactions only allowed on LAN connection  
✅ **IMPLEMENTATION**: All transaction operations (`/transactions/create/`, `/transactions/qr-scanner/`) are **physically LAN-only**  
✅ **VPN RESTRICTION**: VPN connections are **completely blocked** from performing transactions  

✅ **REQUIREMENT**: App communication only to authorized devices  
✅ **IMPLEMENTATION**: Only devices in network diagram can access app (Raspberry Pi, Armory PC, Developer PC)  
✅ **SECURITY**: Unauthorized IP ranges are blocked and logged  

✅ **REQUIREMENT**: Router has internet but app not visible  
✅ **IMPLEMENTATION**: App runs on LAN-only port 8443, no internet exposure  
✅ **VPN ACCESS**: Secure tunnel for authorized remote inventory viewing only  

### 1.2 Purpose
This policy establishes **strict compliance controls** for remote access to ArmGuard inventory viewing while maintaining **absolute transaction security** on physical LAN.

### 1.3 Scope
This policy applies to authorized personnel requiring remote inventory access:
- Field Commanders (inventory oversight)
- Armorers (off-site inventory monitoring)  
- Emergency Operations Personnel (critical equipment status)
- Authorized Military Personnel (status checking)

---

## 2. Access Control Matrix

### 2.1 Physical LAN Access (Required for Transactions)

#### Authorized Devices ONLY:
- ✅ **Raspberry Pi Server** (192.168.x.x)
- ✅ **Armory PC** (192.168.x.x)  
- ✅ **Developer PC** (192.168.x.x)

#### Permitted Operations:
- ✅ **ALL Transactions** (create, edit, delete, QR scanning)
- ✅ **User Management** (registration, role assignment)
- ✅ **Inventory Management** (add, edit, delete equipment)
- ✅ **Administrative Functions** (system configuration)
- ✅ **Print Operations** (labels, reports)

### 2.2 VPN Remote Access (READ-ONLY Inventory)

#### Commander Access (10.0.0.10-19)
- **Classification**: CONFIDENTIAL
- **Permitted**: Inventory viewing, transaction history, status reports
- **Prohibited**: ❌ Transaction creation, ❌ Equipment modification
- **Session Timeout**: 2 hours
- **Usage**: Remote inventory oversight, emergency status checking

#### Armorer Access (10.0.0.20-39)
- **Classification**: CONFIDENTIAL
- **Permitted**: Inventory viewing, equipment status, maintenance reports
- **Prohibited**: ❌ Transaction creation, ❌ Equipment modification
- **Session Timeout**: 1 hour
- **Usage**: Off-site inventory monitoring, shift handover

#### Emergency Access (10.0.0.40-49)
- **Classification**: CONFIDENTIAL
- **Permitted**: Critical equipment status, emergency inventory
- **Prohibited**: ❌ Transaction creation, ❌ Full inventory access
- **Session Timeout**: 30 minutes
- **Usage**: Emergency response, crisis management

#### Personnel Access (10.0.0.50-199)
- **Classification**: RESTRICTED
- **Permitted**: Personal transaction status, profile viewing
- **Prohibited**: ❌ Transaction creation, ❌ Inventory access
- **Session Timeout**: 15 minutes
- **Usage**: Personal status checking only

---

## 3. Operational Security Procedures

### 3.1 VPN Client Distribution

#### Client Configuration Security
- ✅ **Encrypted Storage**: All client configurations stored with military-grade encryption
- ✅ **Secure Distribution**: Configurations distributed via secure military channels only
- ✅ **Access Logging**: All configuration access logged and monitored
- ✅ **Revocation Capability**: Immediate client revocation in case of compromise

#### Client Devices Requirements
- **Approved Devices Only**: Client configurations only installed on approved military devices
- **Device Security**: Devices must have full disk encryption and screen locks
- **Software Requirements**: Latest WireGuard client software mandatory
- **Update Management**: Devices must receive regular security updates

### 3.2 Network Security Controls

#### Transaction Isolation (CRITICAL)
- 🚨 **ABSOLUTE REQUIREMENT**: ALL transaction operations require physical LAN presence
- ❌ **NEVER PERMITTED**: Transaction creation/modification via VPN connection
- ✅ **ENFORCED BY**: Multiple layers of middleware and application controls
- 📋 **AUDIT REQUIREMENT**: All transaction attempts via VPN logged as security violations

#### VPN Access Restrictions
- **READ-ONLY ONLY**: VPN connections provide inventory viewing capability exclusively
- **NO MODIFICATIONS**: Equipment additions, edits, deletions prohibited via VPN
- **SESSION LIMITS**: Automatic session termination based on role timeout values
- **CONCURRENT LIMITS**: Maximum simultaneous VPN connections enforced per role

### 3.3 Incident Response Procedures

#### Security Violation Response
1. **Immediate Detection**: Automated alerts for unauthorized access attempts
2. **Client Isolation**: Automatic disconnection of offending VPN clients
3. **Investigation Protocol**: Full audit trail review within 1 hour
4. **Reporting Requirement**: Security violations reported to commanding officer within 4 hours
5. **Remediation Action**: Client access revocation and security policy review

#### Compromised Client Response
1. **Immediate Revocation**: Client configuration disabled within 5 minutes
2. **Network Isolation**: Affected network segments isolated if necessary
3. **Forensic Analysis**: Complete analysis of compromised client activity
4. **Re-authentication**: All related personnel re-authenticated
5. **Policy Update**: Security policies updated based on incident lessons learned

| Range | Purpose | Security Level | Max Users |
|-------|---------|----------------|-----------|
| 10.0.0.1 | VPN Gateway | N/A | 1 |
| 10.0.0.10-19 | Field Commanders | HIGH | 10 |
| 10.0.0.20-29 | Armorers | HIGH | 10 |
| 10.0.0.30-39 | Emergency Ops | HIGH | 10 |
| 10.0.0.40-49 | Personnel Mobile | MEDIUM | 10 |
| 10.0.0.50-99 | Reserved | N/A | 50 |

---

## 3. Cryptographic Standards

### 3.1 Encryption Requirements
- **Algorithm**: ChaCha20Poly1305 (preferred) or AES-256-GCM
- **Key Length**: 256-bit minimum
- **Key Exchange**: Curve25519
- **Hash Function**: BLAKE2s
- **Authentication**: Poly1305

### 3.2 Key Management
- **Key Generation**: Cryptographically secure random number generation
- **Key Storage**: Hardware security module (HSM) or secure key storage
- **Key Rotation**: Monthly mandatory rotation for server keys
- **Key Backup**: Offline encrypted backup in military-approved safe
- **Key Destruction**: Secure wipe using DoD 5220.22-M standards

### 3.3 Certificate Authority
- **Root CA**: Military internal certificate authority
- **Intermediate CA**: ArmGuard VPN signing authority  
- **Certificate Lifetime**: 90 days maximum
- **Revocation**: Immediate capability via CRL/OCSP

---

## 4. Network Security Controls

### 4.1 Firewall Rules
```bash
# Inbound Rules
ALLOW UDP 51820 FROM any (WireGuard)
DENY ALL FROM any (default)

# Outbound Rules (VPN clients)
ALLOW TCP 8443 TO 192.168.10.1 (ArmGuard LAN)
ALLOW TCP 443 TO 192.168.10.1 (ArmGuard WAN)  
ALLOW UDP 53 TO 10.0.0.1 (DNS)
DENY ALL TO any (prevent internet through VPN)

# Logging
LOG ALL DENIED connections
LOG ALL VPN authentication attempts
```

### 4.2 Intrusion Detection
- **System**: Suricata or Snort on VPN interface
- **Rules**: Military network security rule set
- **Monitoring**: 24/7 SOC monitoring for anomalies
- **Response**: Automatic connection termination for suspicious activity

### 4.3 DDoS Protection
- **Rate Limiting**: 10 connection attempts per minute per IP
- **Connection Limits**: 5 concurrent connections per user
- **Bandwidth Limiting**: 10 Mbps per connection
- **Fail2Ban**: Automatic IP blocking after 3 failed attempts

---

## 5. Authentication & Authorization

### 5.1 Multi-Factor Authentication
- **Primary Factor**: WireGuard cryptographic keys
- **Secondary Factor**: ArmGuard username/password
- **Optional Third Factor**: CAC card integration (future enhancement)

### 5.2 User Provisioning Process
1. **Request**: Official military channels with commander approval
2. **Verification**: Identity verification against personnel database
3. **Key Generation**: Secure key generation with user presence
4. **Configuration**: Role-based configuration assignment
5. **Testing**: Mandatory connectivity and security testing
6. **Training**: User training on VPN client usage and security
7. **Documentation**: Complete audit trail of provisioning

### 5.3 Access Revocation
- **Immediate**: Key revocation within 15 minutes of notification
- **Automatic**: Account lockout after 30 days of inactivity  
- **Emergency**: Kill switch capability for all VPN connections
- **Audit**: Complete audit trail of all revocations

---

## 6. Monitoring & Logging

### 6.1 Required Logging
- **Connection Events**: All connect/disconnect events with timestamps
- **Authentication**: All authentication attempts (success/failure)
- **Data Transfer**: Bandwidth usage per connection
- **Security Events**: All security violations and anomalies
- **Administrative**: All configuration changes and key operations

### 6.2 Log Retention
- **Duration**: 7 years minimum (military records retention)
- **Format**: Military standard log format (SIEM compatible)
- **Storage**: Encrypted storage with offline backup
- **Access**: Restricted to authorized security personnel

### 6.3 Real-Time Monitoring
- **Connection Status**: Active connections dashboard
- **Performance Metrics**: Latency, throughput, packet loss
- **Security Alerts**: Real-time alerting for suspicious activity
- **Health Monitoring**: VPN server resource utilization

---

## 7. Incident Response Procedures

### 7.1 Security Incident Classification

#### Level 1: CRITICAL
- **Examples**: Unauthorized access, key compromise, data breach
- **Response Time**: Immediate (< 15 minutes)
- **Actions**: Shutdown all VPN connections, isolate server, notify command
- **Authority**: Base Security Officer, IT Commander

#### Level 2: HIGH
- **Examples**: Multiple failed authentication, unusual access patterns
- **Response Time**: 1 hour
- **Actions**: Block suspicious IPs, increase monitoring, investigate
- **Authority**: IT Security Team, Network Administrator

#### Level 3: MEDIUM
- **Examples**: Performance degradation, minor configuration issues
- **Response Time**: 4 hours
- **Actions**: Monitor, adjust resources, document
- **Authority**: IT Support Team

### 7.2 Emergency Procedures
- **Kill Switch**: Immediate termination of all VPN connections
- **Isolation**: Network isolation of VPN server from production
- **Backup**: Switch to backup authentication system
- **Communication**: Secure communication channels for coordination

---

## 8. Compliance & Auditing

### 8.1 Regulatory Compliance
- **NIST Cybersecurity Framework**: Full compliance required
- **DoD Cybersecurity Standards**: DoD 8570 compliance
- **Military Networks**: Network security protocols compliance
- **Data Protection**: Military data classification handling

### 8.2 Audit Requirements
- **Frequency**: Quarterly internal audits, annual external audit
- **Scope**: Complete security architecture and controls
- **Documentation**: All configurations, procedures, and controls
- **Remediation**: Mandatory remediation of all findings within 30 days

### 8.3 Penetration Testing
- **Frequency**: Semi-annual authorized penetration testing
- **Scope**: VPN infrastructure and ArmGuard integration
- **Methodology**: OWASP and military-approved testing standards
- **Reporting**: Classified report to commanding officer and IT leadership

---

## 9. Business Continuity & Disaster Recovery

### 9.1 Backup Systems
- **Primary**: Main WireGuard server (192.168.10.1)
- **Secondary**: Backup server on different network segment
- **Tertiary**: Cold standby system for disaster recovery
- **Failover**: Automatic failover within 5 minutes

### 9.2 Recovery Procedures
- **Data Loss**: Maximum 1 hour of data loss acceptable
- **Service Recovery**: Maximum 4 hours for full service restoration
- **Key Recovery**: Secure key recovery from offline backup systems
- **Communication**: Emergency communication plan for all stakeholders

---

## 10. Training & Awareness

### 10.1 Required Training
- **Initial**: Mandatory 4-hour VPN security training
- **Annual**: Annual security awareness refresher
- **Role-Specific**: Additional training based on access level
- **Incident Response**: Annual incident response drill participation

### 10.2 Documentation Requirements
- **User Guides**: Role-specific user guides and procedures
- **Security Awareness**: Security best practices and threat awareness
- **Incident Reporting**: Procedures for reporting security incidents
- **Contact Information**: Emergency contact information and procedures

---

## 11. Acceptable Use Policy

### 11.1 Authorized Uses
- **Official Business**: Military duties and authorized operations only
- **Emergency Operations**: Crisis response and emergency procedures
- **Administrative**: System administration and maintenance activities
- **Training**: Authorized training and testing activities

### 11.2 Prohibited Uses
- **Personal Use**: Any non-military or personal activities
- **Unauthorized Access**: Attempting to access unauthorized systems
- **Data Exfiltration**: Unauthorized copying or transmission of data
- **Malicious Activity**: Any activity that could compromise security

### 11.3 Consequences
- **Minor Violations**: Counseling and additional training
- **Major Violations**: Suspension of VPN access, disciplinary action
- **Criminal Violations**: Referral to military law enforcement
- **Security Breaches**: Full investigation and prosecution

---

## 12. Technical Security Requirements

### 12.1 Client Device Requirements
- **Operating System**: Supported OS with latest security updates
- **Antivirus**: Current military-approved antivirus software
- **Firewall**: Host-based firewall enabled and configured
- **Encryption**: Full disk encryption required for mobile devices

### 12.2 Network Requirements
- **Bandwidth**: Minimum 1 Mbps upload/download for VPN connectivity
- **Latency**: Maximum 200ms latency to VPN server
- **Reliability**: Minimum 99.5% network availability
- **DNS**: Secure DNS configuration to prevent DNS hijacking

### 12.3 Server Hardening
- **OS Security**: Military-approved OS hardening standards
- **Service Minimization**: Only essential services enabled
- **Access Control**: Role-based access control for all functions
- **Monitoring**: Comprehensive security monitoring and alerting

---

## 13. Policy Enforcement

### 13.1 Responsibility Matrix

| Role | Responsibilities |
|------|------------------|
| **IT Commander** | Policy approval, resource allocation, incident escalation |
| **Security Officer** | Security oversight, compliance monitoring, incident response |
| **Network Admin** | Technical implementation, monitoring, maintenance |
| **Users** | Policy compliance, incident reporting, security awareness |

### 13.2 Violation Reporting
- **Internal**: Mandatory reporting of all suspected violations
- **Chain of Command**: Reporting through military chain of command
- **Documentation**: Complete documentation of all incidents
- **Investigation**: Thorough investigation of all security violations

---

## 14. Policy Review & Updates

### 14.1 Review Schedule
- **Quarterly**: Technical security controls review
- **Semi-Annual**: Policy and procedure review
- **Annual**: Complete security architecture review
- **Ad-Hoc**: After any security incident or system change

### 14.2 Update Process
- **Draft**: Security team drafts policy updates
- **Review**: Stakeholder review and feedback
- **Approval**: IT Commander and Security Officer approval
- **Implementation**: Coordinated implementation with training
- **Communication**: All users notified of policy changes

---

## 15. Contact Information

### 15.1 Emergency Contacts
- **IT Emergency**: [EMERGENCY_IT_CONTACT]
- **Security Officer**: [SECURITY_OFFICER_CONTACT]  
- **Network Operations**: [NETWORK_OPS_CONTACT]
- **Base Security**: [BASE_SECURITY_CONTACT]

### 15.2 Support Contacts
- **IT Help Desk**: [HELPDESK_CONTACT]
- **VPN Support**: [VPN_SUPPORT_CONTACT]
- **ArmGuard Support**: [ARMGUARD_SUPPORT_CONTACT]

---

## 16. Appendices

### Appendix A: Configuration Templates
See `/vpn_integration/wireguard/configs/` directory

### Appendix B: Client Setup Guides  
See `/vpn_integration/wireguard/client_configs/` directory

### Appendix C: Troubleshooting Procedures
See `IMPLEMENTATION_GUIDE.md` troubleshooting section

### Appendix D: Security Testing Procedures
See `/vpn_integration/wireguard/scripts/security-audit.sh`

---

**Document Control:**
- **Classification**: RESTRICTED
- **Version**: 1.0
- **Last Updated**: February 2026
- **Next Review**: May 2026
- **Approved By**: [IT_COMMANDER_SIGNATURE]
- **Distribution**: Authorized Personnel Only

**This document contains sensitive security information and must be protected in accordance with military information security regulations.**