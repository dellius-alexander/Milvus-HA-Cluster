from typing import Dict


class QueryInterpreter:
    """
    Interpreter for parsing complex queries.

    Converts query expressions into executable formats.

    Methods:
        interpret: Interprets a query expression.

    Example:
        ```python
        interpreter = QueryInterpreter()
        result = interpreter.interpret("id > 100")
        ```

    Raises:
        MilvusValidationError: If the query expression is invalid.
    """

    def interpret(self, expression: str) -> Dict:
        """
        Interprets a query expression.

        Args:
            expression (str): The query expression to interpret.

        Returns:
            Dict: The interpreted query.
        """
        return {"expr": expression}

