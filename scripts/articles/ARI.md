# Asterisk REST Interface (ARI)

## Overview

The Asterisk REST Interface (ARI) is a modern RESTful API introduced in Asterisk version 12 (released in 2014) that provides programmatic control over Asterisk resources through standard HTTP requests. ARI was designed to give developers a clean, standards-based interface for building custom telephony applications without requiring knowledge of Asterisk's internal dialplan scripting or the older management protocols.

Unlike traditional Asterisk interfaces (dialplan, AGI, AMI), ARI treats calls as first-class objects that external applications can create, manipulate, and destroy. This makes it ideal for building sophisticated communications applications using familiar web development languages and patterns.

## Why ARI Was Created

### Limitations of Previous Interfaces

**Dialplan**: Powerful but has limitations:
- Dialplan is interpreted at runtime, making complex logic difficult
- No native support for modern web integration (REST APIs, JSON)
- Business logic embedded in configuration files
- Hard to test and debug

**AGI (Asterisk Gateway Interface)**: External programs control calls but:
- Communication via STDIN/STDOUT is antiquated
- No standard for returning complex data
- Limited event handling
- Deployment complexity

**AMI (Asterisk Manager Interface)**: TCP-based event/action protocol:
- XML-based messaging is verbose
- Single connection limits scalability
- Authentication and security limitations
- Not REST-friendly

### What ARI Provides

ARI solves these problems by providing:
- **RESTful interface**: Standard HTTP methods (GET, POST, DELETE)
- **JSON messaging**: Modern data exchange format
- **WebSocket events**: Real-time event delivery
- **Object-oriented model**: Channels, bridges, endpoints as resources
- **Separation of concerns**: Telephony logic in your app, not in Asterisk

## ARI Architecture

### Core Concepts

#### Stasis Application
A Stasis application is a named component within Asterisk that receives control of a channel (call). When a call enters a Stasis application, Asterisk sends all events about that call to the external application via WebSocket, and the application controls what happens next through API calls.

#### Channels
A channel represents a single call leg — essentially one participant in a call. When someone calls into Asterisk and is sent to a Stasis application, a channel is created. When a call is bridged between two parties, two channels exist (one for each participant).

#### Bridges
A bridge is a container that mixes media between channels. When you create a bridge and add two channels to it, those callers can hear each other and are connected. Bridges can be:
- **Mixing**: All participants can talk to all other participants (conference)
- **Holding**: Media is absorbed (on-hold music, voicemail deposit)

#### Endpoints
An endpoint represents a configurable destination for SIP calls — typically a SIP phone or external SIP provider.

### The Request Flow

```
[Caller] → [Asterisk] → Stasis Application (your code)
                            ↓
                     WebSocket Events
                            ↓
                     /channels, /bridges, etc.
                            ↓
                     Your application controls call
```

Example flow:
1. An inbound SIP call arrives at Asterisk
2. Dialplan routes call to Stasis application "myapp"
3. Asterisk creates a channel and sends "ChannelCreated" event via WebSocket
4. Your application receives the event via WebSocket
5. Your application decides what to do (play a prompt, collect digits, answer, etc.)
6. Your application sends API calls (POST /channels/{id}/answer)
7. Asterisk executes the action and sends back a result event
8. Repeat until call ends

## ARI Endpoints

### Channels
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /channels | Originate a new call |
| GET | /channels | List all active channels |
| GET | /channels/{channelId} | Get channel details |
| POST | /channels/{channelId}/answer | Answer the call |
| POST | /channels/{channelId}/hangup | Hang up the call |
| POST | /channels/{channelId}/ring | Play ringback |
| POST | /channels/{channelId}/play | Play media to caller |
| POST | /channels/{channelId}/record | Record caller audio |
| POST | /channels/{channelId}/dial | Dial another party |
| POST | /channels/{channelId}/moh | Put on music on hold |
| POST | /channels/{channelId}/snoop | Whisper/barge into call |

### Bridges
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /bridges | Create a bridge |
| GET | /bridges | List active bridges |
| GET | /bridges/{bridgeId} | Get bridge details |
| POST | /bridges/{bridgeId}/addChannel | Add channel to bridge |
| POST | /bridges/{bridgeId}/removeChannel | Remove channel |
| POST | /bridges/{bridgeId}/destroy | Delete bridge |

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /endpoints | List all endpoints (SIP phones) |
| GET | /endpoints/{tech}/{id} | Get endpoint status |

### Recordings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /recordings | List stored recordings |
| GET | /recordings/stored/{name} | Get recording details |
| DELETE | /recordings/stored/{name} | Delete recording |

### Sounds
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /sounds | List available prompts |
| GET | /sounds/{soundId} | Get sound file details |

## WebSocket Events

When your application registers with a Stasis application, it receives a WebSocket connection. All events related to channels in that application are pushed to the WebSocket.

### Event Types

**Channel Lifecycle**
- ChannelCreated
- ChannelDestroyed
- ChannelStateChanged

**Communication**
- ChannelEnteredBridge
- ChannelLeftBridge
- ChannelTalkingStarted
- ChannelTalkingStopped

**DTMF**
- ChannelDtmfReceived

**Playback**
- PlaybackStarted
- PlaybackFinished

**Recording**
- RecordingStarted
- RecordingFinished

**Error**
- ChannelCallerId
- PeerStatus

### Event Format (JSON)
```json
{
  "type": "ChannelCreated",
  "timestamp": "2026-07-22T10:30:00.123+00:00",
  "channel": {
    "id": "1689935400.1",
    "state": "Ringing",
    "caller": {"name": "John Doe", "number": "+1234567890"},
    "connected": {"name": "", "number": ""},
    "accountcode": "",
    "context": "from-external",
    "exten": "1001",
    "creationtime": "2026-07-22T10:30:00.123+00:00"
  }
}
```

## Example Applications Built with ARI

### Click-to-Call Widget
```javascript
// Originate a call from a web page
async function clickToCall(from, to) {
  // Call from your softphone to the customer
  await fetch('http://asterisk:8088/ari/channels', {
    method: 'POST',
    headers: {
      'Authorization': 'Basic ' + btoa('ari_user:ari_password'),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      endpoint: 'PJSIP/1001',
      extension: to,
      context: 'from-internal',
      priority: 1
    })
  });
}
```

### Screen Pop Integration
```javascript
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);

  if (data.type === 'ChannelAnswered') {
    // Fetch customer record from CRM
    const callerNumber = data.channel.caller.number;
    fetchCustomerRecord(callerNumber)
      .then(record => displayOnScreen(record));
  }
};
```

### IVR with Voice Recognition
```javascript
// Play a prompt and collect speech
async function collectSpeech(channelId) {
  // Play menu prompt
  await fetch(`http://asterisk:8088/ari/channels/${channelId}/play`, {
    method: 'POST',
    headers: { /* auth */ },
    body: JSON.stringify({
      media: 'sound:main-menu',
      lang: 'en'
    })
  });

  // Use speech recognition (external service) to interpret response
}
```

### Click-to-Dial from CRM
```javascript
// Agent clicks phone number in CRM
// CRM calls agent first, then connects customer
async function connectCall(agentExten, customerNumber) {
  const channel = await originateCall(agentExten);
  // Wait for agent to answer
  await waitForState(channel.id, 'Up');

  // Bridge to customer
  await fetch(`http://asterisk:8088/ari/channels/${channel.id}/dial`, {
    method: 'POST',
    body: JSON.stringify({
      caller: customerNumber,
      timeout: 30
    })
  });
}
```

## ARI vs. Other Interfaces

| Feature | ARI | AMI | AGI |
|---------|-----|-----|-----|
| Transport | HTTP/WebSocket | TCP | STDIN/STDOUT |
| Data Format | JSON | Text-based | Text-based |
| Real-time Events | WebSocket | TCP events | Polling |
| Learning Curve | Moderate | Steep | Moderate |
| State Management | Your app | Asterisk | Your app |
| Best For | Modern apps | Monitoring | Legacy scripts |

## Authentication and Security

ARI uses HTTP Basic Authentication:
```
Authorization: Basic base64(username:password)
```

Configure in `ari.conf`:
```ini
[ari_user]
password = mypassword
read_only = no
```

Access control is configured in `http.conf`:
```ini
[general]
enabled = yes
bindaddr = 0.0.0.0
port = 8088
```

Best practices:
- Never expose ARI to the public internet
- Use TLS (https) in production
- Implement rate limiting
- Monitor for brute force attacks
- Use read_only accounts where possible

## Building Applications with ARI

### Technology Stack
Any language that can make HTTP requests and handle WebSockets:
- **Node.js**: Most popular for real-time applications
- **Python**: Flask, FastAPI, ari-py library
- **Ruby**: ari-client gem
- **Go**: ari4go library
- **JavaScript/Browser**: Direct WebSocket in browser

### Popular Libraries

| Language | Library |
|----------|---------|
| Node.js | ari-client, @astarisk/ari |
| Python | ari4python, starpy |
| Go | ari4go |
| Ruby | ari-client |
| PHP | phpari |

### Testing ARI Applications

Use Swagger UI (Asterisk 13+):
```
http://your-asterisk:8088/ari/doc/
```

Interactive API documentation and testing interface.

## Advanced ARI Usage

### Multi-Tenant Applications
Filter events by Stasis app name for different customers or departments.

### Distributed Architectures
Multiple application servers connect to the same Asterisk, each handling different calls.

### Recording Integration
Use ARI to start/stop recordings and store them to external storage (S3, etc.).

### Fax Processing
Receive faxes via T.38 and process them through your application.

## Limitations and Considerations

- Requires Asterisk 12+ (older systems must use AMI or AGI)
- Learning curve for developers new to telephony
- WebSocket connections require careful handling for scaling
- No built-in authentication delegation (must manage credentials)

## Conclusion

ARI represents the modern way to build custom telephony applications on Asterisk. By providing a clean REST API and WebSocket event system, it enables developers to use their existing web development skills to create sophisticated communications solutions. Whether building a click-to-call widget, a full contact center application, or an innovative new communication product, ARI provides the tools needed to make Asterisk a powerful development platform.