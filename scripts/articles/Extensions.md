# PBX Extensions and Internal Dialing

## Overview

A Private Branch Exchange (PBX) extension is a short numeric code, typically 3 to 5 digits, assigned to an individual user, device, department, or service within a telephone system. Extensions enable internal callers to reach each other without traversing the public switched telephone network (PSTN), eliminating external line usage and associated call costs for intra-organization communication.

## How Extensions Work

### Basic Mechanics

When a company deploys a PBX, each phone, user, or service receives a unique extension number. For example:
- Sales team: extensions 100-199
- Support team: extensions 200-299
- Management: extensions 300-399
- Executive assistants: extensions 400-405
- Conference rooms: extensions 500-550

To reach a colleague internally, users simply dial the对方的 extension rather than an external telephone number.

### Internal Routing

When a user dials an extension, the PBX performs a lookup in its internal registration database to determine:
1. Is this a valid extension in the system?
2. Where is the endpoint currently registered (IP address for SIP phones, physical port for analog)?
3. What is the current status (available, busy, in call, do not disturb, unavailable)?

The PBX then completes the connection internally within milliseconds—no external line acquisition is required.

## Types of Extensions

### User Extensions
Assigned to individual employees. These follow the user regardless of which phone they log into in a hot-desking environment.

### Device Extensions
Assigned to specific physical hardware like analog phones, fax machines, or overhead paging systems.

### Department/Group Extensions
A single number that rings multiple phones simultaneously (ring group) or sequentially (hunt group). Useful for departments where any available member should answer.

### Service Extensions
Point to automated services rather than individuals:
- **Voicemail**: Typically *98 or 8500
- **Auto-attendant/Operator**: Usually 0 or 800
- **Conference bridge**: Often 700 or a booking-based system
- **Fax retrieval**: Often 8501
- **Overhead paging**: Often *99 or 60

### Feature Codes
Numeric codes that invoke specific phone system features when dialed:
- *72: Call Forwarding Activate
- *73: Call Forwarding Deactivate
- *74: Speed Dial (program a personal short list)
- *75: Speed Dial 8 (personal directory)
- *67: Caller ID Blocking (per-call)
- *69: Call Return (call back last incoming number)
- *97: Voicemail access from own phone
- *98: Voicemail access (generic)

## SIP Phone Registration

In modern IP-based PBX systems using the Session Initiation Protocol (SIP), extensions are dynamically registered over the network:

1. A SIP phone boots up and sends a REGISTER request to the PBX
2. The request includes the phone's SIP username (typically the extension number) and current IP address
3. The PBX stores this binding in its registration database
4. When calls come in for that extension, the PBX knows where to send the SIP INVITE

This dynamic registration enables:
- **Hot-desking**: An employee can log into any IP phone on the network and receive calls directed to their extension
- **Remote workers**: Employees can register their softphone or SIP hardphone from home or branch offices
- **Failover**: If a phone loses connectivity, the PBX knows immediately and can redirect calls

## Extension Numbering Plans

### Planning Considerations
When designing an extension scheme, consider:
- **Growth projections**: Leave gaps in number ranges for future expansion
- **Department size estimates**: Allocate enough extensions per department
- **Feature codes conflict check**: Ensure extension numbers don't conflict with system feature codes
- **DID mapping**: If you have direct inward dial (DID) numbers, plan how they map to internal extensions
- **Short codes**: Some organizations use 2-3 digit extensions for frequently called numbers

### Common Schemes
- **Sequential**: 1001, 1002, 1003... (common in larger organizations)
- **Departmental blocks**: Sales 100-199, Support 200-299, Engineering 300-399
- **Location-based**: Main office extensions start with 1, branches with 2, remote with 3
- **Functional**: 0 for operator, 9 for outside line access (legacy)

## Extension Features and Capabilities

### Call Forwarding
Users can redirect calls to:
- Another extension
- An external number (mobile, home)
- Voicemail
- Another group of numbers (simultaneous or sequential ring)

### Simultaneous Ring
A single extension can ring multiple devices at once—the user's desk phone, softphone, and mobile can all ring simultaneously when someone calls.

### Find Me / Follow Me
Sophisticated routing that tries a sequence of numbers (desk → mobile → home) if the primary extension is unavailable.

### Do Not Disturb (DND)
When enabled, calls to an extension go directly to voicemail or another predetermined destination without ringing.

### Presence
Real-time status indicators showing whether an extension is:
- Available (green)
- In a call (red)
- Do Not Disturb (orange)
- Away / idle (yellow)
- Offline (gray)

## Extension Security Considerations

### Authorization
Configure which extensions can:
- Make international calls
- Access certain IVR features
- Transfer calls externally
- Access voicemail of other users

### Strong PINs
Voicemail PINs should be strong (avoid 1234, 0000, or extension numbers)

### E911 Considerations
Accurate extension-to-user mapping is critical for emergency calling. When a caller dials 911 from a corporate extension, the system must transmit the caller's physical location and identity to emergency services.

## Extension Management Best Practices

### Documentation
Maintain a current directory of:
- Extension number → User name
- Department / team
- Physical location or work area
- Type of device (hardphone, softphone, analog)

### Regular Audits
- Remove extensions for departed employees promptly
- Reclaim unused extensions periodically
- Verify DND and call forwarding settings for accuracy
- Ensure emergency contact information is current

### User Training
Users should know:
- How to check their voicemail
- How to enable call forwarding
- How to use speed dial features
- Who to contact for support

## Conclusion

Extensions are the fundamental addressing unit within a PBX system. A well-designed extension scheme, combined with proper security controls and regular maintenance, provides the foundation for efficient internal communication and professional call handling.