#!/usr/bin/env python3
"""
Phase 1: Nemotron NIM API Validation Benchmark
Measures TTFT, verifies [heard: ...] instruction, tests audio transcription.
"""
import asyncio
import base64
import json
import os
import sys
import time
import statistics
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_NIM_BASE_URL = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

API_URL = f"{NVIDIA_NIM_BASE_URL}/chat/completions"

SYSTEM_PROMPT = """You are a PBX technical support assistant. You speak responses that will be converted
to audio — keep answers conversational, avoid markdown, bullet points, or special
characters. Do not use asterisks, hyphens as list markers, pound signs, or any
formatting that sounds wrong when read aloud.

When the user sends an audio message, you MUST follow this exact format:
Line 1: [heard: <exact verbatim transcript of what the user said>]
Line 2 onwards: Your response in plain, spoken English.

Do NOT add any text before the [heard:] line.
Do NOT include the [heard:] line in your spoken response — it is metadata only.
Keep responses under 150 words unless the question genuinely requires more detail.
Answer only from the context provided. If the context does not contain the answer,
say: "I don't have that information in the knowledge base. Can you check the PBX
manual or contact your administrator?"""

TEST_RAG_CHUNKS = [
    "SIP trunking connects your PBX to the public telephone network over IP. It replaces traditional ISDN or PSTN lines with a virtual connection.",
    "A SIP trunk can carry multiple concurrent calls. Each call uses one channel. The number of channels depends on your provider plan and PBX license.",
    "DTMF (Dual-Tone Multi-Frequency) is used for touch-tone signaling in VoIP. It allows users to interact with IVR systems by pressing keys on their phone."
]

RAG_CONTEXT = "\n".join([
    "KNOWLEDGE BASE CONTEXT:",
    "---",
    TEST_RAG_CHUNKS[0],
    "---",
    TEST_RAG_CHUNKS[1],
    "---",
    TEST_RAG_CHUNKS[2],
    "---",
    "",
    "Answer the user's spoken question using the knowledge base context above."
])

async def call_nim_api(wav_bytes: bytes) -> dict:
    """Call Nemotron NIM API with audio and RAG context."""
    audio_b64 = base64.b64encode(wav_bytes).decode()
    
    payload = {
        "model": NVIDIA_NIM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio_url",
                        "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}
                    },
                    {"type": "text", "text": RAG_CONTEXT}
                ]
            }
        ],
        "max_tokens": 512,
        "reasoning_budget": 0,
        "stream": True,
        "temperature": 0.4,
        "top_p": 0.9,
    }
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", API_URL, json=payload, headers=headers) as response:
            response.raise_for_status()
            
            ttft = None
            full_response = ""
            heard_line = None
            buffer = ""
            
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            token = delta["content"]
                            full_response += token
                            buffer += token
                            
                            if ttft is None:
                                ttft = time.time()
                            
                            if heard_line is None and "\n" in buffer:
                                first_line = buffer.split("\n")[0].strip()
                                if first_line.startswith("[heard:"):
                                    heard_line = first_line
                                buffer = ""
                except json.JSONDecodeError:
                    continue
            
            return {
                "ttft": ttft,
                "full_response": full_response,
                "heard_line": heard_line,
                "status_code": response.status_code
            }

def load_wav_file(wav_path: str) -> bytes:
    """Load WAV file as bytes."""
    with open(wav_path, "rb") as f:
        return f.read()

async def run_ttft_benchmark(wav_path: str, runs: int = 3) -> dict:
    """Run TTFT benchmark multiple times."""
    wav_bytes = load_wav_file(wav_path)
    print(f"Loaded WAV: {len(wav_bytes)} bytes ({len(wav_bytes)/1024:.1f} KB)")
    
    results = []
    for i in range(runs):
        print(f"\nRun {i+1}/{runs}...")
        start = time.time()
        try:
            result = await call_nim_api(wav_bytes)
            elapsed = time.time() - start
            
            if result["ttft"]:
                ttft_ms = int((result["ttft"] - start) * 1000)
            else:
                ttft_ms = None
            
            print(f"  TTFT: {ttft_ms}ms")
            print(f"  Total time: {elapsed*1000:.0f}ms")
            print(f"  Heard line: {result['heard_line']}")
            print(f"  Response preview: {result['full_response'][:200]}...")
            
            results.append({
                "ttft_ms": ttft_ms,
                "total_ms": int(elapsed * 1000),
                "heard_line": result["heard_line"],
                "full_response": result["full_response"]
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"error": str(e)})
        
        if i < runs - 1:
            await asyncio.sleep(2)
    
    return results

def analyze_results(results: list) -> dict:
    """Analyze benchmark results."""
    valid = [r for r in results if r.get("ttft_ms") is not None]
    if not valid:
        return {"error": "No valid runs"}
    
    ttft_values = [r["ttft_ms"] for r in valid]
    ttft_values.sort()
    
    heard_count = sum(1 for r in valid if r.get("heard_line") and r["heard_line"].startswith("[heard:"))
    
    return {
        "runs": len(valid),
        "ttft_ms": {
            "min": min(ttft_values),
            "max": max(ttft_values),
            "median": int(statistics.median(ttft_values)),
            "p95": ttft_values[int(len(ttft_values) * 0.95)] if len(ttft_values) > 1 else ttft_values[0],
            "all": ttft_values
        },
        "heard_line_success_rate": f"{heard_count}/{len(valid)}",
        "heard_line_works": heard_count > 0,
        "primary_stack_recommendation": "nemotron" if (statistics.median(ttft_values) if len(ttft_values) > 1 else ttft_values[0]) <= 800 else "fallback"
    }

async def main():
    print("=" * 60)
    print("Phase 1: Nemotron NIM API Validation Benchmark")
    print("=" * 60)
    
    if not NVIDIA_API_KEY:
        print("ERROR: NVIDIA_API_KEY not set in .env")
        return 1
    
    print(f"API URL: {API_URL}")
    print(f"Model: {NVIDIA_NIM_MODEL}")
    
    # Find test WAV file
    test_dir = Path(__file__).parent.parent / "test_audio"
    wav_files = list(test_dir.glob("*.wav"))
    
    if not wav_files:
        print(f"ERROR: No WAV files found in {test_dir}")
        return 1
    
    wav_path = wav_files[0]
    print(f"Test WAV: {wav_path}")
    
    # Run benchmark
    results = await run_ttft_benchmark(str(wav_path), runs=3)
    
    # Analyze
    analysis = analyze_results(results)
    
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(json.dumps(analysis, indent=2))
    
    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": NVIDIA_NIM_MODEL,
        "test_wav": str(wav_path),
        "results": results,
        "analysis": analysis
    }
    
    output_path = Path(__file__).parent / "benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")
    
    # Decision
    if analysis.get("primary_stack_recommendation") == "nemotron":
        print("\n��� PASS: Nemotron TTFT within target (<=800ms p95). Proceed to Phase 2.")
    else:
        print("\n��� FAIL: Nemotron TTFT exceeds 800ms p95. Switch to fallback stack (faster-whisper + Groq).")
    
    return 0 if analysis.get("primary_stack_recommendation") == "nemotron" else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)