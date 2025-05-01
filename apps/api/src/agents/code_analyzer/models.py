from pydantic import BaseModel, Field


class Filter(BaseModel):
    """
    A specific file to filter out during code search.
    """

    reason: str = Field(description="Why this file was filtered")
    file_path: str = Field(description="Path to the file to filter")
    is_persistent: bool = Field(
        description="Whether this filter persists between queries"
    )

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison.

        :param other: Object to compare with
        :return: True if objects are equal, False otherwise
        """
        if not isinstance(other, Filter):
            return False
        return (
            self.file_path == other.file_path
            and self.is_persistent == other.is_persistent
        )

    def __hash__(self) -> int:
        """
        Makes Filter hashable.

        :return: Hash value for this object
        """
        return hash((self.file_path, self.is_persistent))
