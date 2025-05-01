"""
Helper functions for formatting bug reports and their artifacts.
"""

import re

from src.agents.recording_bug_report.recording_bug_report_agent import BugReport
from src.schemas.core.common import (
    ArtifactType,
    ComponentSelectionArtifact,
    ConsoleLogArtifact,
    ReportAssetModel,
    ReproductionStepsArtifact,
    SelectedComponent,
)


def enrich_bug_report(bug_report: BugReport) -> str:
    """
    Enriches a bug report by inlining all text artifacts where they are referenced.

    :param bug_report: The bug report result containing the report text and text models
    :return: Enriched bug report text with inlined artifacts
    """
    enriched_text: str = bug_report.report

    artifact_pattern = "|".join([f"{t.value}_[a-z0-9]+" for t in ArtifactType])
    pattern = rf"(!?\[.*?\])\(({artifact_pattern})\)"

    def replace_reference(match: re.Match[str]) -> str:
        text_part: str = match.group(1)
        artifact_id: str = match.group(2)

        if artifact_id not in bug_report.text_models:
            return match.group(0)

        artifact_model: ReportAssetModel = bug_report.text_models[artifact_id]

        if artifact_model.content_type == ArtifactType.CONSOLE_LOG:
            log_data: ConsoleLogArtifact = ConsoleLogArtifact.model_validate(
                artifact_model.data
            )
            log_content: str = log_data.log.output
            return f"{text_part}\n```\n{log_content}\n```"

        elif artifact_model.content_type == ArtifactType.REPRODUCTION_STEPS:
            repro_data: ReproductionStepsArtifact = (
                ReproductionStepsArtifact.model_validate(artifact_model.data)
            )
            steps: str = repro_data.steps
            return f"{text_part}\n{steps}"

        elif artifact_model.content_type == ArtifactType.COMPONENT_SELECTION:
            component_data: ComponentSelectionArtifact = (
                ComponentSelectionArtifact.model_validate(artifact_model.data)
            )
            description: str = component_data.description
            annotation: str = component_data.annotation
            component: SelectedComponent = component_data.component

            component_text: str = (
                f"\nComponent Details:"
                f"\n- Description: {description}"
                f"\n- Annotation: {annotation}"
            )

            return f"{text_part}\n{component_text}\n{component.artifact_xml}"

        return match.group(0)

    enriched_text = re.sub(pattern, replace_reference, enriched_text)

    return enriched_text
