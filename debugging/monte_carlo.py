"""
Monte Carlo debugging configuration for LangSmith
"""
import os
import asyncio
from typing import Dict, List, Any, Optional
from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Run, Example
import logging

logger = logging.getLogger(__name__)

class MonteCarloDebugger:
    """Monte Carlo debugging for the doctor appointment system"""
    
    def __init__(self, langsmith_client: Optional[Client] = None):
        self.client = langsmith_client
        self.debug_runs = []
        self.evaluation_results = []
    
    async def run_monte_carlo_simulation(self, 
                                       agent_func, 
                                       test_cases: List[Dict[str, Any]], 
                                       num_simulations: int = 10) -> Dict[str, Any]:
        """Run Monte Carlo simulation on the agent"""
        logger.info(f"Starting Monte Carlo simulation with {num_simulations} runs")
        
        results = {
            'success_rate': 0,
            'error_rate': 0,
            'avg_response_time': 0,
            'common_failures': [],
            'performance_metrics': {}
        }
        
        successful_runs = 0
        total_response_time = 0
        error_counts = {}
        
        for simulation in range(num_simulations):
            for test_case in test_cases:
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Run the agent with the test case
                    if asyncio.iscoroutinefunction(agent_func):
                        response = await agent_func(test_case)
                    else:
                        response = agent_func(test_case)
                    
                    end_time = asyncio.get_event_loop().time()
                    response_time = end_time - start_time
                    total_response_time += response_time
                    
                    successful_runs += 1
                    
                    # Log the run for debugging
                    self.debug_runs.append({
                        'simulation': simulation,
                        'test_case': test_case,
                        'response': response,
                        'response_time': response_time,
                        'success': True
                    })
                    
                except Exception as e:
                    error_type = type(e).__name__
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                    
                    logger.error(f"Simulation {simulation} failed: {e}")
                    
                    self.debug_runs.append({
                        'simulation': simulation,
                        'test_case': test_case,
                        'error': str(e),
                        'error_type': error_type,
                        'success': False
                    })
        
        # Calculate metrics
        total_runs = num_simulations * len(test_cases)
        results['success_rate'] = successful_runs / total_runs
        results['error_rate'] = 1 - results['success_rate']
        results['avg_response_time'] = total_response_time / successful_runs if successful_runs > 0 else 0
        results['common_failures'] = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        logger.info(f"Monte Carlo simulation completed. Success rate: {results['success_rate']:.2%}")
        return results
    
    async def evaluate_agent_performance(self, 
                                       agent_func, 
                                       test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate agent performance using LangSmith evaluation"""
        if not self.client:
            logger.warning("LangSmith client not available for evaluation")
            return {}
        
        evaluation_results = []
        
        for test_case in test_cases:
            try:
                # Create evaluation example
                example = Example(
                    inputs=test_case,
                    outputs={"expected": test_case.get("expected_output", "")}
                )
                
                # Run evaluation
                result = await evaluate(
                    agent_func,
                    data=[example],
                    evaluators=[self._create_custom_evaluator()],
                    client=self.client
                )
                
                evaluation_results.append(result)
                
            except Exception as e:
                logger.error(f"Evaluation failed for test case {test_case}: {e}")
        
        return {
            'evaluation_results': evaluation_results,
            'total_evaluations': len(evaluation_results),
            'successful_evaluations': len([r for r in evaluation_results if r.get('success', False)])
        }
    
    def _create_custom_evaluator(self):
        """Create custom evaluator for the doctor appointment system"""
        def custom_evaluator(run: Run, example: Example) -> Dict[str, Any]:
            """Custom evaluation logic"""
            score = 0
            feedback = []
            
            # Check if response contains expected keywords
            expected_keywords = ['dentist', 'doctor', 'appointment', 'availability']
            response_text = str(run.outputs.get('messages', []))
            
            for keyword in expected_keywords:
                if keyword.lower() in response_text.lower():
                    score += 0.25
                    feedback.append(f"Contains '{keyword}'")
            
            # Check response length (not too short, not too long)
            if 50 <= len(response_text) <= 1000:
                score += 0.25
                feedback.append("Appropriate response length")
            
            # Check if response asks for more information when needed
            if 'please specify' in response_text.lower() or 'need more information' in response_text.lower():
                score += 0.25
                feedback.append("Asks for clarification appropriately")
            
            # Check if response is helpful
            if any(word in response_text.lower() for word in ['help', 'assist', 'available', 'schedule']):
                score += 0.25
                feedback.append("Provides helpful information")
            
            return {
                'key': 'custom_evaluation',
                'score': min(score, 1.0),
                'feedback': feedback,
                'success': score >= 0.5
            }
        
        return custom_evaluator
    
    def generate_debug_report(self) -> str:
        """Generate a comprehensive debug report"""
        report = []
        report.append("=" * 50)
        report.append("MONTE CARLO DEBUG REPORT")
        report.append("=" * 50)
        
        # Summary statistics
        total_runs = len(self.debug_runs)
        successful_runs = len([r for r in self.debug_runs if r.get('success', False)])
        
        report.append(f"Total Runs: {total_runs}")
        report.append(f"Successful Runs: {successful_runs}")
        report.append(f"Success Rate: {successful_runs/total_runs:.2%}" if total_runs > 0 else "Success Rate: N/A")
        
        # Error analysis
        error_types = {}
        for run in self.debug_runs:
            if not run.get('success', False):
                error_type = run.get('error_type', 'Unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if error_types:
            report.append("\nError Analysis:")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {error_type}: {count} occurrences")
        
        # Performance analysis
        response_times = [r.get('response_time', 0) for r in self.debug_runs if r.get('success', False)]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            report.append(f"\nPerformance Analysis:")
            report.append(f"  Average Response Time: {avg_time:.2f} seconds")
            report.append(f"  Min Response Time: {min(response_times):.2f} seconds")
            report.append(f"  Max Response Time: {max(response_times):.2f} seconds")
        
        report.append("=" * 50)
        return "\n".join(report)

# Global Monte Carlo debugger
monte_carlo_debugger = MonteCarloDebugger()

def setup_monte_carlo_debugging(langsmith_client: Optional[Client] = None):
    """Setup Monte Carlo debugging"""
    global monte_carlo_debugger
    monte_carlo_debugger = MonteCarloDebugger(langsmith_client)
    logger.info("Monte Carlo debugging initialized")

async def run_debug_simulation(agent_func, test_cases: List[Dict[str, Any]], num_simulations: int = 10):
    """Run a debug simulation"""
    return await monte_carlo_debugger.run_monte_carlo_simulation(agent_func, test_cases, num_simulations)

def get_debug_report():
    """Get the current debug report"""
    return monte_carlo_debugger.generate_debug_report()
