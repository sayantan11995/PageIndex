import argparse
import os
import json
import traceback
from pageindex import *
from types import SimpleNamespace as config


def find_pdfs(input_dir):
    """Recursively find all PDF files in a directory."""
    pdf_files = []
    for root, _, files in os.walk(input_dir):
        for f in sorted(files):
            if f.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, f))
    return pdf_files


def process_pdf(pdf_path, opt):
    """Process a single PDF and return the parsed structure."""
    return page_index_main(pdf_path, opt)


def main():
    parser = argparse.ArgumentParser(
        description='Batch process a directory of PDFs and output parsed JSON files preserving directory hierarchy.'
    )
    parser.add_argument('--input_dir', type=str, required=True,
                        help='Path to the input directory containing PDF files')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Path to the output directory for JSON results')

    parser.add_argument('--model', type=str, default='gpt-4o-2024-11-20',
                        help='Model to use (or Azure deployment name via AZURE_OPENAI_DEPLOYMENT env var)')

    parser.add_argument('--toc-check-pages', type=int, default=20,
                        help='Number of pages to check for table of contents')
    parser.add_argument('--max-pages-per-node', type=int, default=10,
                        help='Maximum number of pages per node')
    parser.add_argument('--max-tokens-per-node', type=int, default=20000,
                        help='Maximum number of tokens per node')

    parser.add_argument('--if-add-node-id', type=str, default='yes',
                        help='Whether to add node id to the node')
    parser.add_argument('--if-add-node-summary', type=str, default='yes',
                        help='Whether to add summary to the node')
    parser.add_argument('--if-add-doc-description', type=str, default='no',
                        help='Whether to add doc description to the doc')
    parser.add_argument('--if-add-node-text', type=str, default='no',
                        help='Whether to add text to the node')

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.input_dir):
        raise ValueError(f"Input directory not found: {args.input_dir}")

    # Find all PDFs
    pdf_files = find_pdfs(args.input_dir)
    if not pdf_files:
        print(f"No PDF files found in: {args.input_dir}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) in: {args.input_dir}")

    # Build config
    opt = config(
        model=args.model,
        toc_check_page_num=args.toc_check_pages,
        max_page_num_each_node=args.max_pages_per_node,
        max_token_num_each_node=args.max_tokens_per_node,
        if_add_node_id=args.if_add_node_id,
        if_add_node_summary=args.if_add_node_summary,
        if_add_doc_description=args.if_add_doc_description,
        if_add_node_text=args.if_add_node_text,
    )

    succeeded = []
    failed = []

    for i, pdf_path in enumerate(pdf_files, 1):
        # Compute relative path to preserve directory hierarchy
        rel_path = os.path.relpath(pdf_path, args.input_dir)
        rel_dir = os.path.dirname(rel_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        # Mirror directory structure in output
        output_subdir = os.path.join(args.output_dir, rel_dir) if rel_dir else args.output_dir
        os.makedirs(output_subdir, exist_ok=True)
        output_file = os.path.join(output_subdir, f"{pdf_name}_structure.json")

        print(f"\n[{i}/{len(pdf_files)}] Processing: {rel_path}")

        try:
            result = process_pdf(pdf_path, opt)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"  -> Saved: {output_file}")
            succeeded.append(rel_path)

        except Exception as e:
            print(f"  -> FAILED: {e}")
            traceback.print_exc()
            failed.append((rel_path, str(e)))

    # Print summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total:     {len(pdf_files)}")
    print(f"Succeeded: {len(succeeded)}")
    print(f"Failed:    {len(failed)}")

    if failed:
        print("\nFailed files:")
        for path, error in failed:
            print(f"  - {path}: {error}")

    print(f"\nOutput directory: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
