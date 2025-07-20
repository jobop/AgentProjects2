# Multi-Agent System API Documentation

## A2A Protocol API

### Overview

The Agent-to-Agent (A2A) Protocol provides standardized communication between agents in the multi-agent system.

### Base URL

Each agent exposes A2A endpoints at their configured base URL:
- Common Agent: `http://localhost:8000`
- User Research Agent: `http://localhost:8001`
- Product Manager Agent: `http://localhost:8002`
- UI Designer Agent: `http://localhost:8003`

### Authentication

Currently, no authentication is required for local development. In production, implement appropriate authentication mechanisms.

## Endpoints

### 1. Get Agent Capabilities

**GET** `/a2a/capabilities`

Returns the list of capabilities supported by the agent.

#### Response

```json
{
  "agent_id": "user_research_agent",
  "agent_name": "User Research Agent",
  "capabilities": [
    "market_analysis",
    "user_surveys", 
    "persona_creation",
    "competitive_analysis"
  ]
}
```

### 2. Send A2A Request

**POST** `/a2a/request`

Send a request to another agent to execute a specific capability.

#### Request Body

```json
{
  "message_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:00Z",
  "sender_id": "common_agent",
  "recipient_id": "user_research_agent",
  "message_type": "request",
  "capability": "market_analysis",
  "parameters": {
    "industry": "fitness apps",
    "target_market": "mobile users",
    "analysis_type": "competitive"
  },
  "context": {
    "project_id": "fitness-app-2024",
    "user_preferences": {"focus": "mobile-first"}
  },
  "require_response": true
}
```

#### Response

```json
{
  "message_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:05Z",
  "sender_id": "user_research_agent",
  "recipient_id": "common_agent",
  "message_type": "response",
  "request_id": "original-request-uuid",
  "success": true,
  "result": {
    "analysis_type": "competitive",
    "industry": "fitness apps",
    "findings": [
      "Market growing at 15% annually",
      "Key competitors focus on gamification",
      "Wearable integration is trending"
    ],
    "recommendations": [
      "Focus on unique value proposition",
      "Implement social features",
      "Consider AR/VR integration"
    ]
  },
  "error": null
}
```

### 3. Health Check

**GET** `/a2a/health`

Check if the agent is running and healthy.

#### Response

```json
{
  "status": "healthy",
  "agent_id": "user_research_agent"
}
```

## Agent Capabilities

### User Research Agent

#### market_analysis

Analyze market trends and competitive landscape.

**Parameters:**
- `industry` (string): Target industry
- `target_market` (string): Specific market segment  
- `analysis_type` (string): Type of analysis (competitive, trend, opportunity)

**Example Response:**
```json
{
  "analysis_type": "market_trends",
  "industry": "fitness apps",
  "findings": [...],
  "recommendations": [...],
  "methodology": "SWOT + Porter's Five Forces",
  "confidence_level": "High"
}
```

#### user_surveys

Design and analyze user surveys.

**Parameters:**
- `survey_type` (string): Type of survey
- `target_audience` (string): Target user group
- `questions` (array): Specific questions (optional)

#### persona_creation

Create detailed user personas.

**Parameters:**
- `research_data` (object): Input research data
- `persona_count` (number): Number of personas to create
- `target_segments` (array): Target user segments

#### competitive_analysis

Analyze competitors and market positioning.

**Parameters:**
- `competitors` (array): List of competitors
- `analysis_framework` (string): Framework to use
- `focus_areas` (array): Specific areas to analyze

### Product Manager Agent

#### requirements_analysis

Analyze and document product requirements.

**Parameters:**
- `project_type` (string): Type of project
- `stakeholder_input` (object): Input from stakeholders
- `constraints` (object): Project constraints

#### feature_prioritization

Prioritize features based on business value and effort.

**Parameters:**
- `features` (array): List of features to prioritize
- `criteria` (object): Prioritization criteria
- `business_goals` (array): Business objectives

#### roadmap_planning

Create product roadmaps and release plans.

**Parameters:**
- `timeline` (string): Planning timeline
- `features` (array): Features to include
- `resources` (object): Available resources

#### stakeholder_communication

Prepare stakeholder communications and updates.

**Parameters:**
- `audience` (string): Target audience
- `update_type` (string): Type of communication
- `content` (object): Content to communicate

### UI Designer Agent

#### wireframe_creation

Create wireframes and low-fidelity designs.

**Parameters:**
- `screen_type` (string): Type of screen/interface
- `platform` (string): Target platform
- `requirements` (object): Design requirements

#### mockup_design

Create high-fidelity mockups and prototypes.

**Parameters:**
- `design_brief` (object): Design brief and requirements
- `brand_guidelines` (object): Brand guidelines
- `target_platform` (string): Target platform

#### design_review

Review designs for usability and best practices.

**Parameters:**
- `design_files` (array): Design files to review
- `review_criteria` (object): Review criteria
- `target_users` (object): Target user information

#### design_system_management

Create and maintain design systems.

**Parameters:**
- `brand_requirements` (object): Brand requirements
- `platform_targets` (array): Target platforms
- `component_types` (array): Component types needed

## Error Handling

### Error Response Format

```json
{
  "message_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:05Z",
  "sender_id": "agent_id",
  "recipient_id": "sender_id",
  "message_type": "response",
  "request_id": "original-request-uuid",
  "success": false,
  "result": null,
  "error": "Detailed error message"
}
```

### Common Error Codes

- **400 Bad Request**: Invalid request format or missing parameters
- **404 Not Found**: Capability not found
- **500 Internal Server Error**: Agent processing error
- **503 Service Unavailable**: Agent temporarily unavailable

## Usage Examples

### Python Client Example

```python
import asyncio
import httpx
from shared.a2a_protocol.client import A2AClient

async def example_usage():
    client = A2AClient("my_agent")
    
    # Get capabilities
    capabilities = await client.discover_capabilities("http://localhost:8001")
    print(f"Available capabilities: {capabilities}")
    
    # Send request
    response = await client.send_request(
        recipient_endpoint="http://localhost:8001",
        capability="market_analysis",
        parameters={
            "industry": "fitness apps",
            "target_market": "mobile users",
            "analysis_type": "competitive"
        },
        context={"project": "fitness-tracker-app"}
    )
    
    if response.success:
        print(f"Analysis result: {response.result}")
    else:
        print(f"Error: {response.error}")
    
    await client.close()

# Run example
asyncio.run(example_usage())
```

### cURL Examples

#### Get Capabilities
```bash
curl -X GET http://localhost:8001/a2a/capabilities
```

#### Send Request
```bash
curl -X POST http://localhost:8001/a2a/request \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "test_client",
    "recipient_id": "user_research_agent",
    "capability": "market_analysis",
    "parameters": {
      "industry": "fitness apps",
      "target_market": "mobile users"
    },
    "context": {},
    "require_response": true
  }'
```

## Best Practices

### 1. Request Design

- **Be Specific**: Provide clear, specific parameters
- **Include Context**: Pass relevant context information
- **Handle Errors**: Always check response success status
- **Timeout Handling**: Implement appropriate timeouts

### 2. Performance

- **Concurrent Requests**: Use async/await for concurrent operations
- **Connection Pooling**: Reuse HTTP connections when possible
- **Response Caching**: Cache responses when appropriate

### 3. Error Handling

- **Graceful Degradation**: Handle agent unavailability gracefully
- **Retry Logic**: Implement exponential backoff for retries
- **Logging**: Log all interactions for debugging

### 4. Security

- **Input Validation**: Validate all input parameters
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Authentication**: Add authentication for production deployments

## WebSocket Support (Future)

Future versions will support WebSocket connections for real-time communication:

```javascript
// Future WebSocket API
const ws = new WebSocket('ws://localhost:8001/a2a/ws');

ws.on('message', (data) => {
  const message = JSON.parse(data);
  // Handle real-time updates
});

ws.send(JSON.stringify({
  type: 'subscribe',
  capabilities: ['market_analysis']
}));
```

## Rate Limits

Current development setup has no rate limits. Production deployments should implement:

- **Per-agent limits**: 100 requests/minute per agent
- **Per-capability limits**: 10 requests/minute for complex operations
- **Burst allowance**: 20 requests in 10-second windows

## Monitoring

### Health Checks

All agents provide health check endpoints for monitoring:

```bash
# Check all agents
curl http://localhost:8000/a2a/health  # Common Agent
curl http://localhost:8001/a2a/health  # User Research
curl http://localhost:8002/a2a/health  # Product Manager  
curl http://localhost:8003/a2a/health  # UI Designer
```

### Metrics

Agents expose metrics for monitoring:
- Request count by capability
- Response times
- Error rates
- Agent load levels 