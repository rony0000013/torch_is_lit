from tonic_validate import Benchmark, ValidateApi, ValidateScorer

# Function to simulate getting a response and context from your LLM
# Replace this with your actual function call
def get_rag_response(question):
    return {
        "llm_answer": "Paris",
        "llm_context_list": ["Paris is the capital of France."]
    }

benchmark = Benchmark(questions=["What is the capital of France?"], answers=["Paris"])
# Score the responses for each question and answer pair
scorer = ValidateScorer()
run = scorer.score(benchmark, get_rag_response)
validate_api = ValidateApi("k2e6nq4eBNf845-OBs8156AYwvUCGTsMMYV_UMmBOS8")
validate_api.upload_run("52d088f3-211c-4bbe-b57b-f710401514ed", run)