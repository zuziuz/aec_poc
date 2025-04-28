import streamlit as st
import base64
from processor import PDFExtractor, VehicleTitle

# Set the page title and configure the layout for side-by-side display
st.set_page_config(
    page_title="Vehicle Data Extractor",
    layout="wide"
)

# Display the application title
st.title("Vehicle Data Extractor")


def display_pdf(file):
    """
    Display a PDF using Mozilla's PDF.js viewer for better browser compatibility.
    """
    # Get the PDF bytes
    pdf_bytes = file.getvalue()

    # Create a download button for the PDF
    st.download_button(
        label="📥 Download PDF",
        data=pdf_bytes,
        file_name="document.pdf",
        mime="application/pdf"
    )

    # Encode PDF to base64
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

    # Use PDF.js viewer with the base64 data (using version 5.0.375 as specified)
    pdf_js_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Viewer</title>
        <style>
            #pdf-container {{
                width: 100%;
                height: 750px;
                overflow: auto;
                background: #fafafa;
                border: 1px solid #e0e0e0;
            }}
            .pdf-page-canvas {{
                display: block;
                margin: 5px auto;
                border: 1px solid #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <div id="pdf-container"></div>

        <script type="module">
            // Import the PDF.js library (using ES modules)
            import * as pdfjsLib from 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.0.375/pdf.min.mjs';

            // Set the worker source path
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.0.375/pdf.worker.min.mjs';

            // Base64 data of the PDF
            const pdfData = atob('{base64_pdf}');

            // Convert base64 to Uint8Array
            const pdfBytes = new Uint8Array(pdfData.length);
            for (let i = 0; i < pdfData.length; i++) {{
                pdfBytes[i] = pdfData.charCodeAt(i);
            }}

            // Load the PDF document
            const loadingTask = pdfjsLib.getDocument({{ data: pdfBytes }});
            loadingTask.promise.then(function(pdf) {{
                console.log('PDF loaded');

                // Container for all pages
                const container = document.getElementById('pdf-container');

                // Render pages sequentially
                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
                    pdf.getPage(pageNum).then(function(page) {{
                        const scale = 1.5;
                        const viewport = page.getViewport({{scale: scale}});

                        // Create canvas for this page
                        const canvas = document.createElement('canvas');
                        canvas.className = 'pdf-page-canvas';
                        canvas.width = viewport.width;
                        canvas.height = viewport.height;
                        container.appendChild(canvas);

                        // Render PDF page into canvas context
                        const context = canvas.getContext('2d');
                        const renderContext = {{
                            canvasContext: context,
                            viewport: viewport
                        }};
                        page.render(renderContext);
                    }});
                }}
            }}).catch(function(error) {{
                console.error('Error loading PDF:', error);
                document.getElementById('pdf-container').innerHTML = 
                    '<div style="color: red; padding: 20px;">Error loading PDF. Please try downloading instead.</div>';
            }});
        </script>
    </body>
    </html>
    """

    # Display the PDF.js viewer HTML
    st.components.v1.html(pdf_js_html, height=800)


def display_vehicle_data(vehicle_data: VehicleTitle):
    """
    Display the extracted vehicle data in a clean format
    """
    # Create a card-like container for the data
    with st.container():
        st.subheader("Vehicle Information")

        # Display each field with formatting
        fields = {
            "Title State": vehicle_data.title_state,
            "Title Type": vehicle_data.title_type,
            "VIN": vehicle_data.vehicle_vin,
            "Year": vehicle_data.vehicle_year,
            "Make": vehicle_data.vehicle_make,
            "Model": vehicle_data.vehicle_model,
            "Title Number": vehicle_data.title_number,
            "Registered Owner": vehicle_data.vehicle_registered_owner,
            "First Reassignment": vehicle_data.first_reassignment
        }

        for label, value in fields.items():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"**{label}:**")
            with col2:
                st.markdown(f"{value}")
            st.divider()


# Create a file uploader for PDF files
uploaded_file = st.file_uploader("Upload or drag and drop a PDF file", type=["pdf"])

# Process the uploaded PDF file
if uploaded_file is not None:
    # Initialize the PDFExtractor with Gemini API key from Streamlit secrets
    api_key = st.secrets["config"]["gemini_api_key"]
    few_shot_examples_path = st.secrets["config"]["few_shot_examples_path"]
    extractor = PDFExtractor(api_key=api_key, few_shot_examples_path=few_shot_examples_path)

    # Display a spinner while processing
    with st.spinner("Extracting vehicle data from PDF..."):
        try:
            # Extract vehicle data from the uploaded PDF
            vehicle_data = extractor.extract_data_from_uploaded_file(uploaded_file)

            # Create two columns for side-by-side display
            col1, col2 = st.columns(2)

            # Display PDF in the left column
            with col1:
                st.subheader("PDF Document")
                display_pdf(uploaded_file)

            # Display extracted fields in the right column
            with col2:
                display_vehicle_data(vehicle_data)

        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            # Additional debugging information
            st.error("Please check the logs for more details.")
            import traceback

            st.code(traceback.format_exc())
else:
    # Display instructions when no file is uploaded
    st.info("Please upload a PDF file to extract vehicle title information.")

    # Show empty placeholder for the layout
    col1, col2 = st.columns(2)
    with col1:
        st.empty()
    with col2:
        st.empty()