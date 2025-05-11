import requests
from scipy.stats import pearsonr
from novelpy.indicators import Uzzi2013, Foster2015, Lee2015, Wang2017
from novelpy.utils.cooc_utils import create_cooc
import json
import os
from collections import defaultdict
import matplotlib.pyplot as plt

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


def get_references(paper, flag):    
    # If flag == 1, it is a reference's reference that we are getting!

    references_ofPaper = paper.get('referenced_works', []) # make a list of references
    temp_references = []
    print(f"Fetching {len(references_ofPaper)} references...")
    for i, ref in enumerate(references_ofPaper):
        if not isinstance(ref, dict):
            work_id = ref.split('/')[-1]
        else:
            work_id = 'W' + str(ref['id'])
        url = f"https://api.openalex.org/works/{work_id}" 
        response = requests.get(url) # Get the object of the reference paper
        if response.status_code == 200:
            data = response.json()
            if flag == 1:
                modified_ref = {}
                modified_ref['id'] = int(data['id'].split('/')[-1].lstrip('W'))
                modified_ref['year'] = data.get('publication_year', 0)
                data = modified_ref
                print(f"Reference {i+1}/{len(references_ofPaper)} is: ", data)
            temp_references.append(data)
    return temp_references

# Step 2: Retrieve reference list of given paper, determine the citation score of each paper in the reference list
def citation_scores(i, paper):
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
    print(f"Fetching the references for paper {i}...")
    references_ofPaper = get_references(paper, 0)
    print(f"References fetched for paper {i}!")
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
    min = sorted_citation_scores[len(sorted_citation_scores)-1]['citation_normalized_percentile']['value']
    if min == None:
        min = 0

    print(f"There are {num_references} references with citation scores!")
    print("Mean citation score: ", mean_citation)
    avg_ref_citationScore.append(mean_citation)
    print("Maximum citation score is: ", max)
    max_ref_citationScore.append(max)
    print("Minimum citation score is: ", min)
    min_ref_citationScore.append(min)

def modify(i, paper):
    # for paper we need id, year, referenced_works
    print(f"Modifying paper {i}...")
    modified_paper = {}
    modified_paper['id'] = int(paper['id'].split('/')[-1].lstrip('W'))
    modified_paper['year'] = paper.get('publication_year', 0)

    references = modify_reference(i, paper['referenced_works'])
    modified_paper['referenced_works'] = references
    print(f"Paper {i} modified!")
    return modified_paper

def modify_reference(i, references):
    print(f"Modifying the references for paper {i}...")
    modified_references = []
    for ref in references:
        modified_ref = {}
        modified_ref['id'] = int(ref['id'].split('/')[-1].lstrip('W'))
        modified_ref['year'] = ref.get('publication_year', 0)
        modified_ref['referenced_works'] = ref['referenced_works']
        modified_references.append(modified_ref)
    print(f"References modified for paper {i}!")
    return modified_references

# Step 3: Calculate the Pearson coefficients between the citation 
# of each paper in set P and each of: average citation count of reference list, 
# max- citation, and min-citation
def pearson():
    coeff_avg = pearsonr(citation_counts_P, avg_ref_citationScore)
    coeff_min = pearsonr(citation_counts_P, min_ref_citationScore)
    coeff_max = pearsonr(citation_counts_P, max_ref_citationScore)
    print("Pearson correlation and P-value of average citations: ", coeff_avg.statistic, coeff_avg.pvalue)
    print("Pearson correlation and P-value of min citations: ", coeff_min.statistic, coeff_min.pvalue)
    print("Pearson correlation and P-value of max citations: ", coeff_max.statistic, coeff_max.pvalue)
    # Step 4:  calculate the Pearson correlation
    # between the citation score of the paper and the Number of topics generated by the reference list
    coeff_topics = pearsonr(citation_counts_P, num_of_topics)
    print("Pearson correlation and P-value of number of topics: ", coeff_topics.statistic, coeff_topics.pvalue)

def save_papers_by_year(paper):
    """
    Save papers into files by year as required by Novelpy.
    Each year gets its own JSON file with all papers from that year.
    """

    output_dir = "Data/docs/papers"
    os.makedirs(output_dir, exist_ok=True)

    papers_by_year = defaultdict(list)

    references = paper['referenced_works']

    if references:
        papers_by_year[paper['year']].append(paper)
        for ref in references:
            ref['referenced_works'] = get_references(ref, 1)
            papers_by_year[ref['year']].append(ref)

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

def get_novelty_indicators(min, max, year):
    # Create co-occurrence network for references    
    print(f"Now creting cooc for focal year {year}")
    cooc = create_cooc(
    collection_name="papers",
    year_var="year",
    var="referenced_works",
    sub_var="id",
    time_window=range(min - 10, max),
    weighted_network=True,
    self_loop=True
    )
    cooc.main()

    for focal_year in range(year-10, year):
        
        try:
            print(f"Now calculating Uzzi for focal year {focal_year}")
            Uzzi = Uzzi2013(
                collection_name="papers",
                id_variable="id",
                year_variable="year",
                variable="referenced_works",
                sub_variable="id",
                focal_year=focal_year,
            )
            Uzzi.get_indicator()
        except FileNotFoundError:
            print(f"No files for focal year {focal_year}!")
        except AttributeError:
            print(f"No references for focal year {focal_year}!")

        try:
            print(f"Now calculating Foster for focal year {focal_year}")
            Foster = Foster2015(
                collection_name="papers",
                id_variable="id",
                year_variable="year",
                variable="referenced_works",
                sub_variable="id",
                focal_year=focal_year,
                starting_year = 1949,
                community_algorithm = "Louvain",
                density = True
            )
            Foster.get_indicator()
        except FileNotFoundError:
            print(f"No files for focal year {focal_year}!")
        except AttributeError:
            print(f"No references for focal year {focal_year}!")

        try: # does not save results :(
            print(f"Now calculating Lee for focal year {focal_year}")
            Lee = Lee2015(
                collection_name="papers",
                id_variable="id",
                year_variable="year",
                variable="referenced_works",
                sub_variable="id",
                focal_year=focal_year
            )
            Lee.get_indicator()
        except FileNotFoundError:
            print(f"No files for focal year {focal_year}!")
        except AttributeError:
            print(f"No references for focal year {focal_year}!")

        try: # does not save results :(
            print(f"Now calculating Lee for focal year {focal_year}")
            Wang = Wang2017(
                collection_name="papers",
                id_variable="id",
                year_variable="year",
                variable="referenced_works",
                sub_variable="id",
                focal_year=focal_year,
                time_window_cooc=3,
                n_reutilisation=1
            )
            Wang.get_indicator()
        except FileNotFoundError:
            print(f"No files for focal year {focal_year}!")
        except AttributeError:
            print(f"No references for focal year {focal_year}!")


# Defining main function
def main():
    P = retrieve_papers() # Step 1
    with open("SNA/papers.json", 'w') as f: # save to a json file
            json.dump(P, f, indent=2)
    for i, paper in enumerate(P, 0):
        citation_scores(i, paper) # Step 2, 3, 4
        paper = modify(i, paper)
        P[i] = paper
    pearson() # Step 3, 4

    min_year = min([p['year'] for p in P])
    max_year = max([p['year'] for p in P])

    for i, paper in enumerate(P, 1):
        print(f"Adding paper {i}")
        save_papers_by_year(paper)
    for i, paper in enumerate(P, 1):
        print(f"Getting novelty indicators for paper {i}")
        get_novelty_indicators(min_year, max_year, paper['publication_year'])

if __name__=="__main__":
    main()
