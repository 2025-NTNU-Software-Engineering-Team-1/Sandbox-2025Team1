# AI Checker Test Problem

This test problem demonstrates the AI Checker feature which allows custom checkers to use AI APIs for semantic evaluation.

## Features

- **AI-enabled Custom Checker**: The checker receives `AI_API_KEY` and `AI_MODEL` environment variables
- **Network Access**: When AI is enabled, the checker has restricted network access to Google AI APIs only
- **15-second Timeout**: AI-enabled checkers have a fixed 15-second timeout

## Test Cases

### Task 1 (50 points)
- Case 0: Simple factual question (capital of France)
- Case 1: Math question (2+2)

### Task 2 (50 points)
- Case 0: Conceptual question (recursion definition)
- Case 1: Technical question (binary search complexity)

## meta.json Configuration

```json
{
    "customChecker": true,
    "aiChecker": {
        "enabled": true,
        "model": "gemini-2.5-flash"
    }
}
```

## How the AI Checker Works

1. The Sandbox calls Backend API `/problem/<id>/checker-api-key` to get the actual API key
2. The checker runs in a container with `system_router` providing network access to Google AI endpoints only
3. Environment variables `AI_API_KEY` and `AI_MODEL` are injected
4. The checker can call Gemini API for semantic evaluation

## Usage

To test this problem:
1. Build the system_router Docker image: `docker build -t noj-system-router:latest Sandbox/system_router/`
2. Ensure an AI API key is configured in the course's AI settings
3. Create a problem with this test data and enable AI Checker in the pipeline settings
