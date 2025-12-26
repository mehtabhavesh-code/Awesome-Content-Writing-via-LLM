#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper Citation Management Tool - Complete Workflow
Integrates paper synchronization, citation count retrieval, and README update processes
"""

import json
import re
import requests
from datetime import datetime
import sys
import time

class CitationWorkflow:
    def __init__(self):
        self.readme_file = 'README.md'
        self.citations_file = 'citations.json'
        self.api_delay = 1  # API request interval (seconds), fixed at 1 second
        self.skip_recent_hours = 24  # Skip papers updated within the last 24 hours
        
    def print_header(self, title, width=80):
        """Print formatted header"""
        print("-"*width)
        print(f"{title:^{width}}")
        print("-"*width)
    
    def print_step(self, step_num, total_steps, description):
        """Print step information"""
        print(f"\n[Step {step_num}/{total_steps}] {description}")
    
    def extract_authors_from_readme(self, title):
        """Extract author information for a specific paper from README.md"""
        try:
            with open(self.readme_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the position of the paper title
            title_pattern = r'\*\*' + re.escape(title) + r'\*\*'
            match = re.search(title_pattern, content)
            if not match:
                return "Paper title not found"
            
            # Search for author information after the title position
            start_pos = match.end()
            line_content = content[start_pos:start_pos+500].split('\n')[0]  # Only search on the same line
            
            # README format: **Title** [[paper]](link) [Author Info] [Optional Note] [![citation badge
            # Need to skip [[paper]](link) parts and find the first [content] that doesn't start with [[
            
            # Regex: Skip all [[...]](...) format links and find the first standalone [Author Info]
            # Format: [Author Info] after [[paper]](link) or [[paper]](link) [[code]](link)
            author_pattern = r'(?:\[\[[^\]]+\]\]\([^)]*\)\s*)+\[([^\]]+)\]'
            author_match = re.search(author_pattern, line_content)
            
            if author_match:
                authors = author_match.group(1).strip()
                # Ensure this is author information and not other content (like badge or note)
                if (not authors.startswith('!')  # Not a badge
                    and 'http' not in authors.lower()  # Not a link
                    and len(authors) > 3):  # Has actual content
                    return authors
            
            return "Author information not found"
            
        except Exception as e:
            return f"Extraction failed: {str(e)}"
    
    def extract_titles_from_md(self):
        """Extract paper titles from README.md"""
        try:
            with open(self.readme_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update matching pattern to accommodate different title formats
            pattern = r'\*\*(.*?)\*\*\s*\['
            titles = re.findall(pattern, content)
            
            # Clean titles (remove extra spaces and special characters)
            paper_titles = [title.strip() for title in titles if not title.startswith('[') and len(title.strip()) > 10]
            
            print(f"✅ Successfully extracted {len(paper_titles)} papers from {self.readme_file}")
            return paper_titles
            
        except FileNotFoundError:
            print(f'❌ Error: {self.readme_file} file does not exist')
            sys.exit(1)
        except Exception as e:
            print(f'❌ Error reading {self.readme_file}: {str(e)}')
            sys.exit(1)
    
    def load_citations(self):
        """Load citations.json file"""
        try:
            with open(self.citations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Successfully loaded {self.citations_file}, found {len(data['papers'])} papers")
            return data
        except FileNotFoundError:
            print(f'⚠️  {self.citations_file} file does not exist, will create new file')
            return {'papers': {}}
        except json.JSONDecodeError:
            print(f'❌ Error: {self.citations_file} format is incorrect')
            sys.exit(1)
        except Exception as e:
            print(f'❌ Error reading {self.citations_file}: {str(e)}')
            sys.exit(1)
    
    def save_citations(self, data):
        """Save citations data to file"""
        try:
            with open(self.citations_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'❌ Error saving {self.citations_file}: {str(e)}')
            sys.exit(1)
    
    def sync_papers(self):
        """Step 1: Synchronize paper list between README.md and citations.json"""
        self.print_step(1, 3, "Synchronizing paper list")
        
        # Extract paper titles from README.md
        md_titles = self.extract_titles_from_md()
        
        # Load current citations data
        citations_data = self.load_citations()
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
        
        # Create new citations data, only including papers that exist in md
        new_citations = {'papers': {}}
        added_count = 0
        
        print("\n📋 Starting paper list synchronization...")
        
        # Synchronization processing
        for title in md_titles:
            if title in citations_data.get('papers', {}):
                # Keep existing paper citation data
                new_citations['papers'][title] = citations_data['papers'][title]
            else:
                # Add new paper
                new_citations['papers'][title] = {
                    'title': title,  # Add title field
                    'citations': 0,
                    'last_updated': '1970-01-01-00:00:00'  # Set a very old time to ensure new papers are updated immediately
                }
                print(f"➕ Added new paper: {title}")
                added_count += 1
        
        # Check if there are papers that don't exist in README.md (only remove from data, don't modify README file)
        old_papers = set(citations_data.get('papers', {}).keys())
        removed_papers = old_papers - set(md_titles)
        if removed_papers:
            print(f"\n📋 The following {len(removed_papers)} papers don't exist in README.md, will be removed from data (README file not modified):")
            for title in removed_papers:
                print(f"   - {title}")
        
        # Save updated data
        self.save_citations(new_citations)
        
        print(f"\n✅ Paper list synchronization completed!")
        print(f"   📊 Current total: {len(new_citations['papers'])} papers")
        print(f"   ➕ Newly added: {added_count} papers")
        print(f"   📋 Data cleanup: {len(removed_papers)} papers")
        
        return new_citations
    
    def is_recently_updated(self, last_updated_str):
        """Check if paper was updated within the last 24 hours"""
        try:
            from datetime import timedelta
            
            # Parse last update time
            last_updated = datetime.strptime(last_updated_str, '%Y-%m-%d-%H:%M:%S')
            
            # Calculate time difference
            time_diff = datetime.now() - last_updated
            
            # Return True if less than the skip time threshold
            return time_diff < timedelta(hours=self.skip_recent_hours)
            
        except (ValueError, TypeError):
            # If time format parsing fails, consider it needs updating
            return False
    
    def update_paper_citation(self, title, paper_data, retry_limit=3):
        """Get citation count for a single paper and immediately update JSON file"""
        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        old_citation = paper_data["papers"][title]["citations"]
        search_title = paper_data["papers"][title]["title"]  # Use title field for search
        print(f"\n📖 Paper: '{title}'")
        if search_title != title:
            print(f"🔍 Searching by title: '{search_title}'")
        
        for attempt in range(retry_limit):
            try:
                # Use search API to query paper
                params = {
                    "query": search_title,  # Search using title
                    "fields": "title,citationCount,url,authors",  # Add author information
                    "limit": 10  # Get several matching results to increase probability of finding it
                }
                
                response = requests.get(base_url, params=params, headers=headers)
                
                # Special handling for 429 error, skip without displaying
                if response.status_code == 429:
                    if attempt < retry_limit - 1:
                        print(f"   ⚠️ Attempt {attempt+1}: Rate limit reached, retrying in 1 second...")
                        time.sleep(self.api_delay)  # Fixed 1 second wait time
                        continue
                    else:
                        print(f"   ❌ Maximum retry attempts reached, skipping this paper")
                        return False, "Maximum retry attempts reached"
                
                response.raise_for_status()
                data = response.json()
                
                # Check if there are search results
                if not data.get("data") or len(data["data"]) == 0:
                    if attempt < retry_limit - 1:
                        print(f"   ⚠️ Attempt {attempt+1}: API returned empty results, retrying...")
                        time.sleep(self.api_delay)
                        continue
                    else:
                        print(f"   ❌ Not found: API returned empty results")
                        return False, "API returned empty results"
                
                # Try to find exact matching paper title from results
                found = False
                for paper in data["data"]:
                    if 'title' not in paper or 'citationCount' not in paper:
                        continue
                    
                    # Check if title exactly matches (case-insensitive)
                    if paper['title'].lower() == search_title.lower():
                        new_citation = paper['citationCount']
                        
                        # Display citation change
                        change = new_citation - old_citation
                        if change > 0:
                            change_symbol = f"📈 +{change}"
                        elif change < 0:
                            change_symbol = f"📉 {change}"
                        else:
                            change_symbol = "📊 No change"
                        
                        print(f"   ✅ Update successful: {old_citation} → {new_citation} ({change_symbol})")
                        if 'url' in paper and paper['url']:
                            print(f"   🔗 Paper link: {paper['url']}")
                        
                        # Immediately update data
                        paper_data["papers"][title]["citations"] = new_citation
                        current_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                        paper_data["papers"][title]["last_updated"] = current_time
                        
                        # Immediately save to file
                        self.save_citations(paper_data)
                        
                        found = True
                        return True, new_citation
                
                if not found:
                    # Don't retry, display best match result and author information
                    print(f"   ❌ No exact title match found")
                    
                    if data.get("data") and len(data["data"]) > 0:
                        # Find the highest similarity result (take the first one)
                        best_match = data["data"][0]
                        print(f"   🔍 Best match result:")
                        print(f"      API title: '{best_match.get('title', 'No title')}'")
                        print(f"      Current search: '{search_title}'")
                        
                        # Display author information
                        readme_authors = self.extract_authors_from_readme(title)
                        print(f"      README authors: {readme_authors}")
                        
                        api_authors = "No author information"
                        if 'authors' in best_match and best_match['authors']:
                            author_names = [author.get('name', 'Unknown') for author in best_match['authors'][:5]]  # Only show first 5 authors
                            api_authors = ', '.join(author_names)
                            if len(best_match['authors']) > 5:
                                api_authors += f" and {len(best_match['authors'])} others"
                        print(f"      API authors: {api_authors}")
                        
                        print(f"   📝 If confirmed to be the same paper, please manually modify the title field for this paper in citations.json")
                    
                    return False, "Title not exactly matched"
                        
            except requests.exceptions.HTTPError as e:
                if "429" in str(e):  # Rate limit error, retry
                    if attempt < retry_limit - 1:
                        print(f"   ⚠️ Attempt {attempt+1}: Rate limit reached, retrying in 1 second...")
                        time.sleep(self.api_delay)
                        continue
                    else:
                        print(f"   ❌ Maximum retry attempts reached, skipping this paper")
                        return False, "Maximum retry attempts reached"
                else:
                    if attempt < retry_limit - 1:
                        print(f"   ⚠️ Attempt {attempt+1}: HTTP error ({e}), retrying...")
                        time.sleep(self.api_delay)
                        continue
                    else:
                        print(f"   ❌ API request error: {e}")
                        return False, f"HTTP error"
            except requests.exceptions.RequestException as e:
                if attempt < retry_limit - 1:
                    print(f"   ⚠️ Attempt {attempt+1}: Request exception ({e}), retrying...")
                    time.sleep(self.api_delay)
                    continue
                else:
                    print(f"   ❌ API request error: {e}")
                    return False, "Request exception"
            
            # Wait for a period after successful request to avoid rate limiting
            if attempt < retry_limit - 1:
                time.sleep(self.api_delay)
        
        return False, "Exceeded maximum retry attempts"
    
    def get_citations(self, citations_data):
        """Step 2: Get paper citation counts"""
        self.print_step(2, 3, "Getting latest citation counts")
        
        # Sort paper titles by update date ascending (least recently updated first)
        paper_info = []
        for title, info in citations_data["papers"].items():
            # For papers without last_updated field, set a default value
            last_updated = info.get("last_updated", "1970-01-01-00:00:00")
            paper_info.append({
                "title": title,
                "citations": info["citations"],
                "last_updated": last_updated
            })
        
        # Sort only by update date (oldest first, newest last)
        sorted_papers = sorted(paper_info, key=lambda x: x["last_updated"])
        
        # Extract sorted title list
        paper_titles_ordered = [paper["title"] for paper in sorted_papers]
        
        # Output sorting information
        print(f"\n📊 Paper update priority sorting (total {len(sorted_papers)} papers, sorted by last update time ascending):")
        for i, paper in enumerate(sorted_papers[:5]):  # Only show first 5
            print(f"   {i+1}. Citations: {paper['citations']}, Last updated: {paper['last_updated']}")
        if len(sorted_papers) > 5:
            print(f"   ... {len(sorted_papers)-5} more papers")
        
        # Create a new ordered dictionary, preserving original data structure but in new order
        sorted_data = {"papers": {}}
        for title in paper_titles_ordered:
            sorted_data["papers"][title] = citations_data["papers"][title]
        
        # Save sorted data to original file
        self.save_citations(sorted_data)
        
        # Update citation counts one by one and save immediately
        updated_papers = []
        skipped_papers = []
        skipped_recent = []
        
        need_update_count = 0
        # First count how many papers need updating
        for title in paper_titles_ordered:
            last_updated = sorted_data["papers"][title].get("last_updated", "1970-01-01-00:00:00")
            if not self.is_recently_updated(last_updated):
                need_update_count += 1
        
        print(f"📊 Need to update: {need_update_count} papers, Skipping: {len(paper_titles_ordered) - need_update_count} papers (updated within 24 hours)")
        
        current_update_index = 0
        for index, title in enumerate(paper_titles_ordered):
            # Check if updated within 24 hours
            last_updated = sorted_data["papers"][title].get("last_updated", "1970-01-01-00:00:00")
            if self.is_recently_updated(last_updated):
                skipped_recent.append({
                    "title": title,
                    "last_updated": last_updated
                })
                continue
            
            current_update_index += 1
            print(f"\n🔄 Processing paper {current_update_index}/{need_update_count}")
            
            success, result = self.update_paper_citation(title, sorted_data)
            
            if success:
                old_citations = sorted_data["papers"][title]["citations"] - (result if isinstance(result, int) else 0)
                updated_papers.append({
                    "title": title,
                    "old": old_citations,
                    "new": sorted_data["papers"][title]["citations"],
                    "change": sorted_data["papers"][title]["citations"] - old_citations,
                    "updated_time": sorted_data["papers"][title]["last_updated"]
                })
            else:
                skipped_papers.append({
                    "title": title,
                    "reason": result
                })
            
            # Add delay between requests
            if index < len(paper_titles_ordered) - 1:
                time.sleep(self.api_delay)
        
        # Create detailed report
        print(f"\n✅ Successfully updated: {len(updated_papers)} ({(len(updated_papers)/len(paper_titles_ordered)*100):.1f}%)")
        print(f"⏭️ Skipped (updated within 24 hours): {len(skipped_recent)} ({(len(skipped_recent)/len(paper_titles_ordered)*100):.1f}%)")

        if updated_papers:
            print(f"📈 Successfully updated papers ({len(updated_papers)} papers):")
            for i, paper in enumerate(updated_papers[:10]):  # Only show first 10
                change_symbol = "📈" if paper['change'] > 0 else "📉" if paper['change'] < 0 else "📊"
                print(f"   {i+1}. '{paper['title'][:50]}{'...' if len(paper['title']) > 50 else ''}'")
                print(f"      Citation change: {paper['old']} → {paper['new']} ({change_symbol}{paper['change']:+d})")
            if len(updated_papers) > 10:
                print(f"   ... {len(updated_papers)-10} more papers successfully updated")
        
        
        if skipped_papers:
            print(f"❌ Papers that failed to update ({len(skipped_papers)} papers):")
            for i, paper in enumerate(skipped_papers[:5]):  # Only show first 5
                print(f"   {i+1}. '{paper['title'][:50]}{'...' if len(paper['title']) > 50 else ''}'")
                print(f"      Reason: {paper['reason']}")
            if len(skipped_papers) > 5:
                print(f"   ... {len(skipped_papers)-5} more papers failed to update")
        
        return sorted_data, updated_papers
    
    def update_readme_citations(self, citations_data, updated_papers_list):
        """Step 3: Update citation badges in README.md (strictly protected, only update badges)"""
        self.print_step(3, 3, "Updating citation badges in README.md")
        
        # If no papers need README update
        if not updated_papers_list:
            return True
        
        try:
            with open(self.readme_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
                md_content = original_content  # Keep a copy of original content
        except Exception as e:
            print(f'❌ Failed to read {self.readme_file}: {str(e)}')
            return False
        
        # Only update papers that were actually successfully updated in step 2
        papers_to_update = [paper["title"] for paper in updated_papers_list]
        print(f"📄 Starting to update citation badges for {len(papers_to_update)} papers...")
        
        updated_count = 0
        error_count = 0
        
        # Only iterate through papers that need updating
        for paper_title in papers_to_update:
            try:
                paper_info = citations_data['papers'][paper_title]
                
                # Find exact matching paper title in markdown
                matches = [m.start() for m in re.finditer(r'\*\*' + re.escape(paper_title) + r'\*\*', md_content)]
                
                # Check number of matches
                if len(matches) == 0:
                    print(f"   ⚠️ No matching paper title found: {paper_title}")
                    error_count += 1
                    continue
                elif len(matches) > 1:
                    print(f"   ⚠️ Found multiple matching paper titles: {paper_title}")
                    error_count += 1
                    continue
                
                # Find citation badge after match position
                match_pos = matches[0]
                badge_pattern = r'\[!\[\]\(https://img\.shields\.io/badge/citation-\d+-blue\)\]\(\)'
                badge_match = re.search(badge_pattern, md_content[match_pos:])
                
                if not badge_match:
                    print(f"   ⚠️ Citation badge not found for paper: {paper_title}")
                    error_count += 1
                    continue
                
                # Update citation count
                old_badge = badge_match.group(0)
                new_badge = f'[![](https://img.shields.io/badge/citation-{paper_info["citations"]}-blue)]()'        
                
                # Only replace the first badge after current paper position
                before_match = md_content[:match_pos + badge_match.start()]
                after_match = md_content[match_pos + badge_match.end():]
                md_content = before_match + new_badge + after_match
                
                print(f"   ✅ Successfully updated: '{paper_title[:50]}{'...' if len(paper_title) > 50 else ''}' → {paper_info['citations']} citations")
                updated_count += 1
                
            except Exception as e:
                print(f"   ❌ Error processing paper: {paper_title} - {str(e)}")
                error_count += 1
                continue
        
        # Verify content integrity: check if there are any changes other than citation badges
        print(f"\n🔍 Verifying content integrity...")
        
        # Remove all citation badges for comparison
        original_no_badges = re.sub(r'\[!\[\]\(https://img\.shields\.io/badge/citation-\d+-blue\)\]\(\)', '', original_content)
        updated_no_badges = re.sub(r'\[!\[\]\(https://img\.shields\.io/badge/citation-\d+-blue\)\]\(\)', '', md_content)
        
        if original_no_badges != updated_no_badges:
            print(f"❌ Detected changes other than citation badges, refusing to save to protect README integrity")
            return False
        
        # Save updated README.md
        try:
            with open(self.readme_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"✅ Content integrity verification passed")
            print(f"💾 {self.readme_file} update completed!")
            print(f"   ✅ Successfully updated: {updated_count} citation badges")
            if error_count > 0:
                print(f"   ⚠️ Update failed: {error_count} badges")
            return True
        except Exception as e:
            print(f'❌ Failed to save {self.readme_file}: {str(e)}')
            return False
    
    def run_workflow(self):
        """Run the complete citation management workflow"""
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Step 1: Synchronize paper list
            citations_data = self.sync_papers()
            
            # Step 2: Get citation counts
            updated_data, updated_papers_list = self.get_citations(citations_data)
            
            # Step 3: Update README
            readme_success = self.update_readme_citations(updated_data, updated_papers_list)
            
            # Final report
            
            print(f"\n{'✅' if readme_success else '❌'} Step 3 - README update: {'Completed' if readme_success else 'Failed'}")
            print(f"⏰ Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        except KeyboardInterrupt:
            print(f"\n\n⚠️ User interrupted the workflow")
            print(f"💾 Current progress has been saved to {self.citations_file}")
        except Exception as e:
            print(f"\n\n❌ Workflow execution failed: {str(e)}")
            sys.exit(1)

def main():
    """Main function"""
    workflow = CitationWorkflow()
    workflow.run_workflow()

if __name__ == "__main__":
    main() 