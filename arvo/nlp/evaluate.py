"""
Evaluation harness with canned prompts for testing NLP extraction.
"""

import time
import json
from typing import List, Dict, Any, Optional
from .extract import extract_overrides
from .schema import Overrides, NLPReport


# Golden test prompts
GOLDEN_PROMPTS = [
    "Deploy this Django app on AWS with a small VM in Oregon, add a custom domain api.foo.com and HTTPS; auto-destroy in 24h.",
    "Serverless Python on AWS us-east-1, no DB, 24h TTL",
    "Containerize on AWS, region Oregon, autoscale 1..3",
    "Static Next.js site to CDN with https",
    "Deploy Flask app on t3.medium in us-west-2 with postgres database",
    "Deploy serverless on EC2",
    "Deploy my app with a large VM and custom domain example.com",
    "Deploy containerized app with autoscaling from 2 to 10 instances",
    "Deploy on AWS with micro instance and no database",
    "Deploy static website with CloudFront and SSL",
    "Deploy cheap VM in Northern Virginia",
    "Deploy two replicas in production scale",
    "Deploy with postgres database and custom domain",
    "Deploy on GCP with medium instance",
    "Deploy with autoscaling and HTTPS",
    "Deploy containerized app on Azure",
    "Deploy with no database and 48h TTL",
    "Deploy static site with custom domain and SSL",
    "Deploy with environment variables DEBUG=false and PORT=8080",
    "Deploy with health check at /health endpoint"
]


def evaluate_prompts(
    prompts: Optional[List[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate NLP extraction on a set of prompts.
    
    Args:
        prompts: List of prompts to evaluate (defaults to golden prompts)
        provider: NLP provider to use
        model: Model to use
        output_file: Optional file to save results
        
    Returns:
        Dictionary with evaluation results
    """
    if prompts is None:
        prompts = GOLDEN_PROMPTS
    
    results = {
        "timestamp": time.time(),
        "provider": provider or "default",
        "model": model or "default",
        "total_prompts": len(prompts),
        "results": []
    }
    
    print(f"Evaluating {len(prompts)} prompts with provider: {provider or 'default'}")
    
    for i, prompt in enumerate(prompts, 1):
        print(f"Processing prompt {i}/{len(prompts)}: {prompt[:60]}...")
        
        try:
            start_time = time.time()
            overrides, report = extract_overrides(
                prompt,
                provider=provider,
                model=model,
                timeout_s=15.0
            )
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = {
                "prompt": prompt,
                "overrides": overrides.to_dict(),
                "report": report.to_dict(),
                "duration_ms": duration_ms,
                "success": True
            }
            
        except Exception as e:
            result = {
                "prompt": prompt,
                "error": str(e),
                "success": False
            }
        
        results["results"].append(result)
    
    # Compute summary statistics
    results["summary"] = _compute_summary(results["results"])
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_file}")
    
    # Print summary
    _print_summary(results["summary"])
    
    return results


def _compute_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics from results."""
    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]
    
    if not successful:
        return {
            "total": len(results),
            "successful": 0,
            "failed": len(failed),
            "success_rate": 0.0,
            "avg_duration_ms": 0,
            "avg_confidence": 0.0
        }
    
    durations = [r["duration_ms"] for r in successful]
    confidences = [r["overrides"].get("confidence", 0.0) for r in successful]
    
    return {
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(results),
        "avg_duration_ms": sum(durations) / len(durations),
        "avg_confidence": sum(confidences) / len(confidences),
        "min_confidence": min(confidences),
        "max_confidence": max(confidences)
    }


def _print_summary(summary: Dict[str, Any]) -> None:
    """Print evaluation summary."""
    print("\n" + "="*50)
    print("EVALUATION SUMMARY")
    print("="*50)
    print(f"Total prompts: {summary['total']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['success_rate']:.1%}")
    print(f"Average duration: {summary['avg_duration_ms']:.0f}ms")
    print(f"Average confidence: {summary['avg_confidence']:.2f}")
    print(f"Confidence range: {summary['min_confidence']:.2f} - {summary['max_confidence']:.2f}")
    print("="*50)


def test_specific_cases() -> None:
    """Test specific edge cases and conflicts."""
    test_cases = [
        {
            "name": "Conflicting Infrastructure",
            "prompt": "Deploy serverless on EC2",
            "expected_conflicts": True
        },
        {
            "name": "Domain without SSL",
            "prompt": "Deploy with custom domain example.com",
            "expected_domain": "example.com",
            "expected_ssl": None
        },
        {
            "name": "SSL without Domain",
            "prompt": "Deploy with HTTPS",
            "expected_ssl": True,
            "expected_domain": None
        },
        {
            "name": "Invalid Region",
            "prompt": "Deploy in invalid-region-123",
            "expected_region": None
        },
        {
            "name": "Environment Variables",
            "prompt": "Deploy with DEBUG=true and PORT=8080",
            "expected_env": {"DEBUG": "true", "PORT": "8080"}
        }
    ]
    
    print("Testing specific edge cases...")
    
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print(f"Prompt: {case['prompt']}")
        
        try:
            overrides, report = extract_overrides(case['prompt'])
            
            # Check expected results
            if case.get("expected_conflicts"):
                if report.conflicts:
                    print(f"✓ Expected conflicts found: {report.conflicts}")
                else:
                    print("✗ Expected conflicts not found")
            
            if case.get("expected_domain"):
                if overrides.domain == case["expected_domain"]:
                    print(f"✓ Expected domain: {overrides.domain}")
                else:
                    print(f"✗ Expected domain {case['expected_domain']}, got {overrides.domain}")
            
            if case.get("expected_ssl") is not None:
                if overrides.ssl == case["expected_ssl"]:
                    print(f"✓ Expected SSL: {overrides.ssl}")
                else:
                    print(f"✗ Expected SSL {case['expected_ssl']}, got {overrides.ssl}")
            
            if case.get("expected_region"):
                if overrides.region == case["expected_region"]:
                    print(f"✓ Expected region: {overrides.region}")
                else:
                    print(f"✗ Expected region {case['expected_region']}, got {overrides.region}")
            
            if case.get("expected_env"):
                if overrides.env_overrides == case["expected_env"]:
                    print(f"✓ Expected env vars: {overrides.env_overrides}")
                else:
                    print(f"✗ Expected env vars {case['expected_env']}, got {overrides.env_overrides}")
            
            print(f"Confidence: {overrides.confidence:.2f}")
            print(f"Assumptions: {report.assumptions}")
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")


def benchmark_providers() -> None:
    """Benchmark different providers."""
    providers = ["mock", "openai", "anthropic", "gemini"]
    test_prompts = GOLDEN_PROMPTS[:5]  # Use first 5 prompts for benchmarking
    
    print("Benchmarking providers...")
    
    for provider in providers:
        print(f"\nBenchmarking {provider}...")
        
        try:
            results = evaluate_prompts(
                prompts=test_prompts,
                provider=provider,
                output_file=f"benchmark_{provider}.json"
            )
            
            summary = results["summary"]
            print(f"Success rate: {summary['success_rate']:.1%}")
            print(f"Average duration: {summary['avg_duration_ms']:.0f}ms")
            print(f"Average confidence: {summary['avg_confidence']:.2f}")
            
        except Exception as e:
            print(f"Provider {provider} failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate NLP extraction")
    parser.add_argument("--provider", help="NLP provider to use")
    parser.add_argument("--model", help="Model to use")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--test-cases", action="store_true", help="Run specific test cases")
    parser.add_argument("--benchmark", action="store_true", help="Benchmark all providers")
    
    args = parser.parse_args()
    
    if args.test_cases:
        test_specific_cases()
    elif args.benchmark:
        benchmark_providers()
    else:
        evaluate_prompts(
            provider=args.provider,
            model=args.model,
            output_file=args.output
        )
