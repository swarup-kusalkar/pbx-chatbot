# Asterisk: The Open-Source PBX

## Overview

Asterisk is the world's most widely deployed open-source Private Branch Exchange (PBX) software. Originally created by Mark Spencer at Digium in 1999, Asterisk turns a standard computer into a full-featured telephone system capable of handling VoIP, traditional PSTN lines, and hybrid configurations. The name "Asterisk" (the * symbol) was chosen to represent the system's nature as a wildcard—a complete communications platform limited only by configuration rather than hardware or licensing restrictions.

Asterisk runs on Linux-based operating systems and has become the foundation for countless business telephone systems, service provider offerings, and custom telephony applications worldwide.

## History and Background

Mark Spencer created Asterisk in 1999 while working at Digium, a company he founded. The project started as a solution to the problem of expensive, proprietary business telephone systems. By leveraging the growing power of standard PC hardware and the flexibility of open-source software, Asterisk offered an alternative that was both powerful and affordable.

Digium later developed hardware cards (Digium TDM, Digium TE) to connect Asterisk to traditional telephone lines (T1/E1, PRI, analog). The company also commercialized Asterisk through products like Switchvox (a pre-configured Asterisk PBX) and provided commercial support.

In 2005, Digium acquired the intellectual property behind the Asterisk project and established the Asterisk open-source project under the GNU General Public License (GPL). The project continues to be maintained with contributions from a global community of developers.

## Key Features of Asterisk

### Core Telephony Features
- **Call routing**: Flexible dialplan-based call routing to any destination
- **IVR**: Interactive Voice Response menus for caller interaction
- **Call queuing**: ACD (Automatic Call Distribution) with configurable strategies
- **Voicemail**: Full-featured voicemail with email integration and transcription
- **Conference calling**: Multi-party audio conferences with moderation
- **Music on hold**: Customizable audio for callers on hold or in queue
- **Call parking**: Transfer calls to a parking slot for pickup by any extension
- **Call pickup**: Answer calls ringing on other extensions
- **Call recording**: Record calls to audio files for quality and compliance
- **Call forwarding**: Multiple forwarding modes (busy, no answer, all calls)

### Protocol Support
Asterisk supports multiple VoIP protocols:
- **SIP (Session Initiation Protocol)**: The most common VoIP protocol
- **IAX (Inter-Asterisk eXchange)**: Asterisk's native protocol for peer-to-peer connections
- **H.323**: Legacy VoIP protocol standard
- **MGCP (Media Gateway Control Protocol)**: For controlling media gateways
- **Skinny (SCCP)**: Cisco proprietary protocol

### PSTN Connectivity
Asterisk connects to traditional phone lines through:
- **Analog cards**: FXO/FXS ports for connecting to analog lines and phones
- **T1/PRI cards**: Digital T1, E1, and J1 circuits
- **SS7**: Signaling System 7 for carrier-grade connections
- **VoIP gateways**: External devices that convert between SIP and PSTN
- **SIP trunking**: Direct IP connection to service providers

## Asterisk Architecture

### Modular Design
Asterisk uses a modular architecture where functionality is provided by loadable modules:
- **chan_*.so**: Channel drivers (SIP, IAX2, etc.)
- **app_*.so**: Applications (Voicemail, ConfBridge, etc.)
- **func_*.so**: Dialplan functions for data manipulation
- **res_*.so**: Resources (音乐 on hold, ODBC database, etc.)
- **codec_*.so**: Audio codecs for encoding/decoding

### Channels
A channel in Asterisk represents a single call leg. Each call involves at least one channel (for outbound calls) or two channels (for connected calls, one at each end). Channel drivers abstract the protocol-specific details of different telephony technologies.

### The Dialplan

The dialplan (extensions.conf) is the heart of Asterisk call processing. It defines:
- How calls are routed
- What applications are executed
- How conditions are evaluated

The dialplan is organized into contexts, which are named sections that group extensions and provide isolation between different groups of users or call flows.

**Dialplan syntax example:**
```asterisk
[from-internal]
exten => 100,1,Answer()                    ; Extension 100, first priority
same => n,Wait(1)                          ; Wait 1 second
same => n,Playback(hello-world)            ; Play greeting
same => n,Hangup()                          ; Hang up

exten => 200,1,Goto(ivr,s,1)               ; Transfer to IVR

[ivr]
exten => s,1,Answer()                      ; Start IVR
same => n,Background(main-menu)            ; Play menu
same => n,WaitExten()                       ; Wait for input
exten => 1,1,Goto(sales,s,1)              ; Press 1 for sales
exten => 2,1,Goto(support,s,1)            ; Press 2 for support
```

## Asterisk PBX Configuration

### Extension Configuration (sip.conf / pjsip.conf)
```
[1001]
type=peer
host=dynamic
secret=password123
context=from-internal
displayname=John Smith
```

### Voicemail Configuration (voicemail.conf)
```
[default]
1001 => 1234,John Smith,john@example.com
1002 => 5678,Jane Doe,jane@example.com
```

### Dialplan Logic
Extensions can include sophisticated logic:
- Time-based routing (business hours vs. after-hours)
- Database lookups for caller authentication
- External script execution via AGI
- Integration with HTTP APIs
- Conditional branching based on caller input or system state

## Asterisk GUI Interfaces

While Asterisk is configured through text files, several GUI interfaces make administration easier:

### FreePBX
The most popular Asterisk GUI, developed by Sangoma. Provides:
- Web-based configuration for all major features
- Module system for additional functionality
- Easy IVR creation through visual builder
- Automated provisioning for SIP phones

### elastiCRM / Issabel
Full-featured unified communications platforms built on Asterisk.

### Others
- FreePBX (most popular)
- AsteriskNOW (official Red Hat-based distribution)
- VisionIP
- Custom GUIs built on the Asterisk REST Interface

## Asterisk as a Platform

What sets Asterisk apart is its use as a development platform for custom telephony applications.

### AGI (Asterisk Gateway Interface)
AGI allows external programs to control Asterisk call flow:
- Scripts in any language (PHP, Python, Perl, etc.)
- Receive events and send commands
- Database integration
- Custom business logic
```php
#!/usr/bin/php
<?php
require('phpagi.php');
$agi = new AGI();

$agi->answer();
$agi->text_input_mode(1);  // Collect digits
$digit = $agi->wait_for_digit(5000);

if ($digit == 1) {
    $agi->exec('Goto', 'sales,s,1');
}
```

### AMI (Asterisk Manager Interface)
TCP/IP interface for external applications to:
- Monitor asterisk events in real-time
- Initiate calls (originate)
- Control channels (hangup, transfer, mute)
- Query status of extensions and calls

### FastAGI
AGI over a network connection rather than STDIN/STDOUT:
- Scalable AGI processing
- Load balancing across multiple servers
- Runs on separate machines from Asterisk

### ARI (Asterisk REST Interface)
Modern RESTful API (described in detail separately) for building custom applications using standard web technologies.

## Asterisk Distributions

Several pre-packaged distributions bundle Asterisk with Linux, GUIs, and utilities:

| Distribution | Description |
|-------------|-------------|
| FreePBX | Most popular GUI, extensive module ecosystem |
| AsteriskNOW | Official CentOS-based distribution |
| elastiCRM | Full UC platform |
| Issabel | Feature-rich platform |
| RasPBX | Asterisk on Raspberry Pi |

## Use Cases for Asterisk

### Small Business PBX
Single Asterisk server replacing a legacy PBX, supporting:
- 10-100 extensions
- SIP trunking for external calls
- Voicemail and auto-attendant
- Basic call queues

### Contact Center Platform
Asterisk as the foundation for outbound/inbound call centers:
- Predictive dialers
- ACD queues
- CRM integration
- Recording and quality management
- Multi-tenant for multiple clients

### Service Provider Infrastructure
Telecom carriers using Asterisk for:
- Wholesale VoIP termination
- Hosted PBX (cloud PBX) services
- Calling card and callback platforms
- Conference calling services

### Custom Applications
- Video conferencing (using chan_pjsip with video)
- Custom IVR systems
- Telephony integration with business software
- Emergency notification systems
- Click-to-call from web applications

## Asterisk Performance and Scaling

### Hardware Requirements
- CPU: Multi-core for call processing
- RAM: 1-2 GB for base system, more for larger deployments
- Storage: For recordings, voicemails, logs
- Network: Gigabit for VoIP traffic (low latency critical)

### Capacity
- Small system (single server): 50-100 concurrent calls
- Medium (optimized server): 200-500 concurrent calls
- Large (clustered): 1000+ concurrent calls with distributed architecture

### Performance Tuning
- Disable unused modules
- Optimize codec selection (G.729 vs. G.711)
- Configure jitter buffers appropriately
- Enable hardware acceleration where available

## Conclusion

Asterisk is a powerful, flexible, and cost-effective platform for building telephone systems of any size. Its modular architecture, extensive protocol support, and open-source nature have made it the foundation for everything from small office phone systems to enterprise contact centers and telecommunications services. Whether deployed as a pre-packaged solution like FreePBX or used as a development platform for custom applications, Asterisk provides capabilities that rival or exceed commercial PBX systems at a fraction of the cost.