from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from typing import List, Any
import os
import json
import logging
from pathlib import Path
import tempfile


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleTitle(BaseModel):
    title_state: str = Field(description="State of the vehicle title")
    title_type: str = Field(description="Type of the vehicle title")
    vehicle_vin: str = Field(description="Vehicle VIN number")
    vehicle_year: int = Field(description="Vehicle model year")
    vehicle_make: str = Field(description="Make")
    vehicle_model: str = Field(description="Model")
    title_number: str = Field(description="Number the vehicle title")
    vehicle_registered_owner: str = Field(description="Owner of the vehicle")
    first_reassignment: str = Field(description="First reassignment")


class PDFExtractor:
    """Service for extracting vehicle information from PDFs."""

    def __init__(self, api_key: str, few_shot_examples_path: str = None):
        """
        Initialize PDF extractor with Google API key.

        Args:
            api_key: Google Gemini API key
            few_shot_examples_path: Path to few-shot examples JSON file
        """
        self.client = genai.Client(api_key=api_key)
        self.few_shot_examples_path = few_shot_examples_path

        self.system_prompt = """
        You are an AI assistant that extracts auto vehicle information from PDFs.
        Extract all the needed data.
        Usually every data point except for first_reassignment is in the first page, while first_reassignment is in the second page.
        first_reassignment is usually handwritten, so you have to be extra careful extracting that.
        first_reassignment and vehicle_registered_owner contain business name and full address in most cases.
        Be thorough and accurate in your extraction.
        """

        self.main_prompt = "Please extract the vehicle information from the attached PDF document."

    def create_few_shot_examples(self) -> List[Any]:
        """
        Create few-shot examples for the Gemini model.

        Returns:
            List of example prompts and responses
        """
        if not self.few_shot_examples_path or not os.path.exists(self.few_shot_examples_path):
            return []

        few_shot_examples = []
        with open(self.few_shot_examples_path, "r") as f:
            examples = json.load(f)

        for example in examples:
            filepath = Path(example["pdf_path"])
            if not filepath.exists():
                logger.warning(f"Example PDF file not found: {example['pdf_path']}")
                continue

            few_shot_examples.extend(
                [
                    "Please extract data from the following PDF",
                    types.Part.from_bytes(
                        data=filepath.read_bytes(),
                        mime_type="application/pdf",
                    ),
                    json.dumps(example["expected_output"], indent=2),
                ],
            )

        return few_shot_examples

    def extract_data_from_pdf(self, pdf_data: bytes) -> VehicleTitle:
        """
        Extract vehicle data from PDF data.

        Args:
            pdf_data: PDF file data as bytes

        Returns:
            VehicleTitle object containing extracted vehicle information

        Raises:
            Exception: If extraction fails
        """
        try:
            few_shot_examples = self.create_few_shot_examples()

            response = self.client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=[
                    self.system_prompt,
                    *few_shot_examples,
                    types.Part.from_bytes(
                        data=pdf_data,
                        mime_type="application/pdf",
                    ),
                    self.main_prompt,
                ],
                config={"response_mime_type": "application/json", "response_schema": VehicleTitle},
            )

            # Parse the JSON response
            result = response.parsed
            return result

        except Exception as e:
            logger.error(f"Error extracting vehicle data from PDF: {str(e)}")
            raise

    def extract_data_from_file(self, pdf_file_path: str) -> VehicleTitle:
        """
        Extract vehicle data from a PDF file.

        Args:
            pdf_file_path: Path to PDF file

        Returns:
            VehicleTitle object containing extracted vehicle information
        """
        with open(pdf_file_path, "rb") as f:
            pdf_data = f.read()

        return self.extract_data_from_pdf(pdf_data)

    def extract_data_from_uploaded_file(self, uploaded_file) -> VehicleTitle|None:
        """
        Extract vehicle data from a Streamlit uploaded file.

        Args:
            uploaded_file: Streamlit uploaded file object

        Returns:
            VehicleTitle object containing extracted vehicle information
        """
        # For Streamlit uploaded files, save to temp file first
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_file_path = temp_file.name

        try:
            return self.extract_data_from_file(temp_file_path)
        finally:
            # Clean up the temp file
            os.unlink(temp_file_path)