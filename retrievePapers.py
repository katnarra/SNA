import requests
from scipy.stats import pearsonr
from novelpy.indicators import Uzzi2013
from novelpy.utils.cooc_utils import create_cooc
import json
import os
from collections import defaultdict

base_url = "https://api.openalex.org/works"

params = {
    "search": "Citizen science in water research",
    "filter": "type:article",
    "per-page": 200
}

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

    references_ofPaper = get_references(paper)
    paper['referenced_works'] = references_ofPaper
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
                temp_set.add(topic['display_name'])
            topics_set = topics_set | temp_set # Step 4: Add the topics if they are not already included in topics_set
        print(f"{i}. {data.get('display_name')}, citation percentile: {data['citation_normalized_percentile']['value']}")
    
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
    print("Fetching the references...")
    try:
        references_ofPaper = paper['referenced_works'] # make a list of references
    except:
        return
    temp_references = []
    for ref in references_ofPaper:
        work_id = ref.split('/')[-1]
        url = f"https://api.openalex.org/works/{work_id}" 
        response = requests.get(url) # Get the object of the reference paper
        if response.status_code == 200:
            data = response.json()
            temp_references.append(data)
    print("References fetched!")
    return temp_references

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

def save_papers_by_year(paper):
    """
    Save papers into files by year as required by Novelpy.
    Each year gets its own JSON file with all papers from that year.
    """

    output_dir = "Data/docs/papers"
    os.makedirs(output_dir, exist_ok=True)

    papers_by_year = defaultdict(list)

    papers_by_year[paper['publication_year']].append(paper)

    for ref in paper['referenced_works']:
        ref['referenced_works'] = get_references(ref) # the references of the reference also need to be in dict format containing the year
        # so this will modify them, though it will take some time...

        print(ref)
        papers_by_year[ref['publication_year']].append(ref)
    

    for year, papers in papers_by_year.items():
        file_path = os.path.join(output_dir, f"{year}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = [existing]
                except:
                    existing = []
        else:
            existing = []

        existing_ids = {p['id'] for p in existing if isinstance(p, dict)}
        combined = existing + [p for p in papers if p['id'] not in existing_ids]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2)

def get_novelty_indicators(focal_year):
    # Create co-occurrence network for references
    cooc = create_cooc(
        collection_name="papers",
        year_var="publication_year",
        var="referenced_works",
        sub_var="id",
        time_window=range(focal_year - 10, focal_year),
        weighted_network=True,
        self_loop=True
    )
    cooc.main()

    for year in range(focal_year - 10, focal_year):
        score = Uzzi2013(
            collection_name="papers",
            id_variable="id",
            year_variable="publication_year",
            variable="referenced_works",
            sub_variable="id",
            focal_year=year,
        )
        print(score.get_indicator())


# Defining main function
def main():
    P = retrieve_papers() # Step 1
    for paper in P:
        citation_scores(paper) # Step 2, 3, 4
    pearson() # Step 3, 4

    for i, paper in enumerate(P, 1):
        print(f"Trying to add paper {i}")
        save_papers_by_year(paper)
        get_novelty_indicators(paper['publication_year'])

if __name__=="__main__":
    main()
