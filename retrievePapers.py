import requests
from scipy.stats import pearsonr
import novelpy
import json
import os
from collections import defaultdict

base_url = "https://api.openalex.org/works"

params = {
    "search": "Citizen science in water research",
    "filter": "type:article",
    "per-page": 200
}

references = [] # a list including all the jsons of references per paper, so that they do not need to be
# modified several times

citation_counts_P = [] # how often a paper is cited by other papers
avg_ref_citationScore = [] # average citation count of reference list
min_ref_citationScore = [] # min citation count of reference list
max_ref_citationScore = [] # max citation count of reference list
num_of_topics = [] # number of topics in each paper in list P

# Step 1, retrieve 6 papers
def retrieve_papers():
    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print("Failed with status code: ", response.status_code)

    data = response.json()
    results = data.get("results", [])

    # sort the papers based on how many times the papers have been cited
    sorted_papers = sorted(results, key=lambda x: x.get('cited_by_count'), reverse=True)
            
    print("Top search results for 'Citizen science in water research':\n")
    for i, work in enumerate(sorted_papers, 1):
        print(f"{i}. {work.get('display_name')}, cited: {work.get('cited_by_count')}")

    # get the 6 wanted papers
    P = [sorted_papers[0], sorted_papers[1], sorted_papers[99], sorted_papers[100], sorted_papers[198], sorted_papers[199]]
    for i, work in enumerate(P, 1):
        print(f"{i}. {work.get('display_name')}, cited: {work.get('cited_by_count')}")
    return P

# Step 2: Retrieve reference list of given paper, determine the citation score of each paper in the reference list
def citation_scores(paper):
    num_references = paper.get('referenced_works_count')
    print(f"The paper {paper.get('display_name')} has {num_references} references.")
    if num_references == 0:
        return
    # Step 3: include how often the paper has been cited, only if it has references
    citation_counts_P.append(paper.get('cited_by_count'))

    citations_withScores = []
    citations_withoutScores = []

    mean_citation = 0

    topics_set = set() # For step 4

    print("Fetching references...")
    references_ofPaper = get_references(paper)
    for i, data in enumerate(references_ofPaper, 1):
        citation_percentile = data.get('citation_normalized_percentile')
        if citation_percentile is not None: 
            citations_withScores.append(data) # Add the reference if citation_percentile is a valid value
            mean_citation += citation_percentile['value']
        else:
            data['citation_normalized_percentile'] = {'value' : None}
            citations_withoutScores.append(data) # Add to the other list which will be extended to the end of 'sorted_citation_scores'
            num_references -= 1
        if data['topics']: # Step 4: Check that there are topics for the given reference
            temp_set = set()
            for topic in data['topics']:
                temp_set.add(topic)
            topics_set = topics_set | temp_set # Step 4: Add the topics if they are not already included in topics_set
        print(f"{i}. {data.get('display_name')}, citation percentile: {data['citation_normalized_percentile']['value']}")
    print("References fetched!")
    
    print(f"The {len(topics_set)} topics of references are: {topics_set}")
    num_of_topics.append(len(topics_set)) # Step 4: we wanted to know how many topics in each paper in list P
    paper['topics'] = list(topics_set)

    sorted_citation_scores = sorted(citations_withScores, key=lambda x: x.get('citation_normalized_percentile')['value'], reverse=True)
    sorted_citation_scores.extend(citations_withoutScores)

    # All below are a part of Step 2
    mean_citation = mean_citation / num_references
    max = sorted_citation_scores[0]['citation_normalized_percentile']['value']
    min = sorted_citation_scores[num_references-1]['citation_normalized_percentile']['value']

    print(f"There are {num_references} references with citation scores!")
    print("Mean citation score: ", mean_citation)
    avg_ref_citationScore.append(mean_citation)
    print("Maximum citation score is: ", max)
    max_ref_citationScore.append(max)
    print("Minimum citation score is: ", min)
    min_ref_citationScore.append(min)

def get_references(paper):
    references_ofPaper = paper.get('referenced_works') # make a list of references
    modified_references = []
    for i, ref in enumerate(references_ofPaper, 1):
        work_id = ref.split('/')[-1]
        url = f"https://api.openalex.org/works/{work_id}" 
        response = requests.get(url) # Get the object of the reference paper
        if response.status_code == 200:
            new_ref = {}
            data = response.json()
            new_ref['display_name'] = data['display_name']
            new_ref['citation_normalized_percentile'] = data['citation_normalized_percentile']
            new_ref['publication_year'] = data['publication_year']
            new_ref['id'] = data['id']
            if 'topics' in data:
                new_ref['topics'] = [topic['display_name'] for topic in data['topics']]
            modified_references.append(new_ref)
    references.append(modified_references)
    return modified_references

# Step 3: Calculate the Pearson coefficients between the citation 
# of each paper in set P and each of: average citation count of reference list, 
# max- citation, and min-citation
def pearson():
    coeff_avg = pearsonr(citation_counts_P, avg_ref_citationScore)
    coeff_min = pearsonr(citation_counts_P, min_ref_citationScore)
    coeff_max = pearsonr(citation_counts_P, max_ref_citationScore)
    print("Pearson correlation of average citations: ", coeff_avg.statistic)
    print("Pearson correlation of min citations: ", coeff_min.statistic)
    print("Pearson correlation of max citations: ", coeff_max.statistic)

    # Step 4:  calculate the Pearson correlation
    # between the citation score of the paper and the Number of topics generated by the reference list
    coeff_topics = pearsonr(citation_counts_P, num_of_topics)
    print("Pearson correlation of number of topics: ", coeff_topics.statistic)

import os
import json
import novelpy
from novelpy.indicators import Uzzi2013
from novelpy.utils.cooc_utils import create_cooc

def save_papers_by_year(papers, output_dir):
    """
    Save papers into folders by year as required by Novelpy.
    Each year gets its own JSON file with all papers from that year.
    """
    papers_by_year = {}
    for paper in papers:
        year = paper['publication_year']
        if year is None:
            year = "Unknown"
        papers_by_year.setdefault(year, []).append(paper)

    for year, year_papers in papers_by_year.items():
        year_dir = os.path.join(output_dir)
        os.makedirs(year_dir, exist_ok=True)
        with open(os.path.join(year_dir, f"{year}.json"), 'w', encoding='utf-8') as f:
            json.dump(year_papers, f)

def get_novelty_indicators(article, all_references, focal_year, paper_id):
    base_dir = f"Data/docs/papers/{paper_id}"
    os.makedirs(base_dir, exist_ok=True)

    # Add the target article itself into the dataset
    all_papers = all_references + [article]
    save_papers_by_year(all_papers, base_dir)

    # Create co-occurrence network for references
    cooc = create_cooc(
        collection_name=f"papers/{paper_id}",
        year_var="publication_year",
        var="referenced_works",
        sub_var="topics",
        time_window=range(focal_year - 10, focal_year),
        weighted_network=True,
        self_loop=True
    )
    cooc.main()

    results = {}
    for year in range(focal_year - 10, focal_year):
        score = Uzzi2013(
            collection_name=f"papers/{paper_id}",
            id_variable="id",
            year_variable="publication_year",
            variable="referenced_works",
            sub_variable="topics",
            focal_year=year,
            list_ids=[article['id']]  # Only evaluate novelty of the target article
        )
        print(score.get_indicator())
        # indicators = score.get_indicator()


# Defining main function
def main():
    P = retrieve_papers() # Step 1
    for paper in P:
        citation_scores(paper) # Step 2, 3, 4
    pearson() # Step 3, 4
    for i, paper in enumerate(P, 1):
        print(f"Trying uzzi for paper {i}")
        paper['referenced_works'] = references[i-1]
        get_novelty_indicators(paper, references[i-1], paper['publication_year'], i)

if __name__=="__main__":
    main()

