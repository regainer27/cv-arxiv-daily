import os
import json
import shutil
import logging
import datetime
from pathlib import Path

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)

class ArchiveManager:
    """
    Manage paper archives by year/month/day structure
    """
    def __init__(self, archive_root='./archives', keep_days=30):
        """
        @param archive_root: root directory for archives
        @param keep_days: number of days to keep in main README
        """
        self.archive_root = Path(archive_root)
        self.keep_days = keep_days
        self.archive_root.mkdir(parents=True, exist_ok=True)

    def get_archive_path(self, date_obj):
        """
        Get archive path for a given date
        @param date_obj: datetime.date object
        @return: Path object for archive file
        """
        year = str(date_obj.year)
        month = f"{date_obj.month:02d}"
        day = f"{date_obj.day:02d}"

        # Create directory structure: archives/YYYY/MM/
        archive_dir = self.archive_root / year / month
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Archive filename: YYYY-MM-DD.md
        archive_file = archive_dir / f"{year}-{month}-{day}.md"
        return archive_file

    def archive_old_papers(self, json_file, md_file):
        """
        Archive papers older than keep_days to yearly/monthly folders
        @param json_file: JSON data file path
        @param md_file: Markdown file path
        """
        logging.info(f"Starting archive process for {json_file}")

        # Load current JSON data
        with open(json_file, 'r') as f:
            content = f.read()
            if not content:
                logging.warning("JSON file is empty, skipping archive")
                return
            data = json.loads(content)

        # Current date and cutoff date
        today = datetime.date.today()
        cutoff_date = today - datetime.timedelta(days=self.keep_days)

        logging.info(f"Archiving papers older than {cutoff_date}")

        # Separate papers into recent and old
        recent_data = {}
        archive_data_by_date = {}  # Group by date for archiving

        for keyword, papers in data.items():
            recent_data[keyword] = {}

            for paper_id, paper_content in papers.items():
                # Extract date from paper content
                # Format: |**YYYY-MM-DD**|...
                date_str = self._extract_date(paper_content)

                if date_str:
                    try:
                        paper_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

                        if paper_date >= cutoff_date:
                            # Keep recent papers
                            recent_data[keyword][paper_id] = paper_content
                        else:
                            # Archive old papers
                            if paper_date not in archive_data_by_date:
                                archive_data_by_date[paper_date] = {}
                            if keyword not in archive_data_by_date[paper_date]:
                                archive_data_by_date[paper_date][keyword] = {}
                            archive_data_by_date[paper_date][keyword][paper_id] = paper_content
                    except ValueError:
                        logging.warning(f"Invalid date format for paper {paper_id}: {date_str}")
                        recent_data[keyword][paper_id] = paper_content
                else:
                    # If date not found, keep in recent
                    recent_data[keyword][paper_id] = paper_content

        # Write archived papers to respective date files
        for archive_date, archive_papers in archive_data_by_date.items():
            self._write_archive(archive_date, archive_papers)

        # Update main JSON file with only recent papers
        with open(json_file, 'w') as f:
            json.dump(recent_data, f)

        logging.info(f"Archive completed. Kept {self.keep_days} days of papers in main file")

        # Generate archive index
        self._generate_archive_index()

    def _extract_date(self, paper_content):
        """
        Extract date from paper content string
        @param paper_content: paper string in markdown format
        @return: date string in YYYY-MM-DD format
        """
        import re
        # Match date in format |**YYYY-MM-DD**|
        match = re.search(r'\|\*\*(\d{4}-\d{2}-\d{2})\*\*\|', paper_content)
        if match:
            return match.group(1)
        return None

    def _write_archive(self, date_obj, papers_dict):
        """
        Write archived papers to markdown file
        @param date_obj: datetime.date object
        @param papers_dict: dictionary of papers grouped by keyword
        """
        archive_file = self.get_archive_path(date_obj)

        # If archive file exists, load and merge data
        if archive_file.exists():
            with open(archive_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        else:
            existing_content = ""

        # Generate markdown content
        date_str = date_obj.strftime("%Y.%m.%d")

        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(f"## Archived Papers - {date_str}\n\n")
            f.write(f"> Archived on {datetime.date.today()}\n\n")

            # Write papers by keyword
            for keyword, papers in papers_dict.items():
                if not papers:
                    continue

                f.write(f"### {keyword}\n\n")
                f.write("|Publish Date|Title|Authors|PDF|Code|\n")
                f.write("|---|---|---|---|---|\n")

                for paper_id, paper_content in papers.items():
                    f.write(paper_content)

                f.write("\n")

        logging.info(f"Archived {len(papers_dict)} keyword(s) to {archive_file}")

    def _generate_archive_index(self):
        """
        Generate an index file listing all archives by year/month
        """
        index_file = self.archive_root / "README.md"

        # Collect all archive files
        archives_by_year = {}

        for year_dir in sorted(self.archive_root.iterdir(), reverse=True):
            if not year_dir.is_dir() or year_dir.name == '.git':
                continue

            year = year_dir.name
            archives_by_year[year] = {}

            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue

                month = month_dir.name
                archives_by_year[year][month] = []

                for archive_file in sorted(month_dir.glob("*.md"), reverse=True):
                    archives_by_year[year][month].append(archive_file)

        # Write index file
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write("# CV Arxiv Daily - Archives\n\n")
            f.write(f"> Last updated: {datetime.date.today()}\n\n")
            f.write("This directory contains archived papers organized by year and month.\n\n")
            f.write("## Archive Index\n\n")

            for year in sorted(archives_by_year.keys(), reverse=True):
                f.write(f"### {year}\n\n")

                for month in sorted(archives_by_year[year].keys(), reverse=True):
                    month_name = datetime.date(int(year), int(month), 1).strftime("%B")
                    f.write(f"#### {month_name} ({month})\n\n")

                    for archive_file in archives_by_year[year][month]:
                        rel_path = archive_file.relative_to(self.archive_root)
                        date_str = archive_file.stem  # YYYY-MM-DD
                        f.write(f"- [{date_str}](./{rel_path.as_posix()})\n")

                    f.write("\n")

        logging.info(f"Generated archive index at {index_file}")

def archive_papers(json_readme_path, md_readme_path, keep_days=30, archive_root='./archives'):
    """
    Main function to archive old papers
    @param json_readme_path: path to README JSON file
    @param md_readme_path: path to README markdown file
    @param keep_days: number of days to keep in main README
    @param archive_root: root directory for archives
    """
    manager = ArchiveManager(archive_root=archive_root, keep_days=keep_days)
    manager.archive_old_papers(json_readme_path, md_readme_path)
    logging.info("Archive process completed successfully")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Archive old papers from CV Arxiv Daily")
    parser.add_argument('--json_file', type=str, default='./docs/cv-arxiv-daily.json',
                        help='Path to JSON data file')
    parser.add_argument('--md_file', type=str, default='README.md',
                        help='Path to markdown file')
    parser.add_argument('--keep_days', type=int, default=30,
                        help='Number of days to keep in main README')
    parser.add_argument('--archive_root', type=str, default='./archives',
                        help='Root directory for archives')

    args = parser.parse_args()

    archive_papers(
        json_readme_path=args.json_file,
        md_readme_path=args.md_file,
        keep_days=args.keep_days,
        archive_root=args.archive_root
    )
