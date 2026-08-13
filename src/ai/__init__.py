"""
AI Package.
"""

from src.ai.active_learning_loop import ActiveLearningManager, CorrectionFeedback
from src.ai.autonomous_agent_swarm import AgentRole, AgentStatus, AutonomousAgentSwarm, SwarmAgentState
from src.ai.cashflow_forecaster import CashFlowForecaster, CashFlowForecastResult
from src.ai.financial_solvency_analyzer import CorporateSolvencyAnalyzer, FinancialSolvencyReport
from src.ai.fraud_detector import FraudGuardrailEngine, FraudRiskAssessment
from src.ai.gpu_cluster_orchestrator import DistributedGPUClusterOrchestrator, GPUNodeStatus
from src.ai.multimodal_reconciler import MultiModalReconciler, ReconciliationMatchResult
from src.ai.neural_trial_balance_sentinel import AnomalyReport, NeuralTrialBalanceSentinel, TrialBalanceAccountItem
from src.ai.nlu_voice_command_executor import (
    AutonomousVoiceCommandExecutor,
    BulgarianNLUCommandParser,
    ExecutionCommandType,
    ExecutionMode,
    ExecutionStatus,
    VoiceExecutionResponse,
)
from src.ai.synthetic_stress_harness import SyntheticStressHarness
from src.ai.unsloth_classifier import UnslothTransactionClassifier
from src.ai.unsloth_finetune import BulgarianAccountingDatasetGenerator, UnslothFineTuner
from src.ai.voice_accounting_assistant import VoiceAccountingAssistant, VoiceQueryResult

# Backward compatibility aliases
ActiveLearningLoop = ActiveLearningManager
AccountantCorrection = CorrectionFeedback
UnslothFineTuneManager = UnslothFineTuner
CognitiveAgent = AgentRole
SwarmStatus = AgentStatus

__all__ = [
    "UnslothTransactionClassifier",
    "BulgarianAccountingDatasetGenerator",
    "UnslothFineTuner",
    "UnslothFineTuneManager",
    "ActiveLearningManager",
    "ActiveLearningLoop",
    "CorrectionFeedback",
    "AccountantCorrection",
    "FraudGuardrailEngine",
    "FraudRiskAssessment",
    "CashFlowForecaster",
    "CashFlowForecastResult",
    "VoiceAccountingAssistant",
    "VoiceQueryResult",
    "AutonomousVoiceCommandExecutor",
    "BulgarianNLUCommandParser",
    "ExecutionMode",
    "ExecutionCommandType",
    "ExecutionStatus",
    "VoiceExecutionResponse",
    "CorporateSolvencyAnalyzer",
    "FinancialSolvencyReport",
    "DistributedGPUClusterOrchestrator",
    "GPUNodeStatus",
    "SyntheticStressHarness",
    "MultiModalReconciler",
    "ReconciliationMatchResult",
    "AutonomousAgentSwarm",
    "AgentRole",
    "CognitiveAgent",
    "AgentStatus",
    "SwarmStatus",
    "SwarmAgentState",
    "NeuralTrialBalanceSentinel",
    "TrialBalanceAccountItem",
    "AnomalyReport",
]
