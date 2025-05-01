from pydantic import BaseModel


class RuntimeResult(BaseModel):
    stdout: list[str]
    stderr: list[str]
    url_tested: str

    def xml_error(self, idx: int) -> str:
        return f"""
<error_{idx}>
<url_tested>
{self.url_tested}
</url_tested>
<console_errors>
{"\n".join([result.strip() for result in self.stderr])}
</console_errors>
</error_{idx}>
""".strip()
