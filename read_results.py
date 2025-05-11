import os, json
import pandas as pd
import math
import matplotlib.pyplot as plt
import seaborn as sns


def read_uzzi_results():
    path_to_json = "Result/uzzi/referenced_works/"
    json_files = [pos_json for pos_json in os.listdir(path_to_json) if pos_json.endswith('.json')]

    data = []

    for file in json_files:
        year = int(file.replace(".json", "")) # remove the .json from the filename to get the year
        filepath = os.path.join(path_to_json, file)
        with open(filepath, "r") as f:
            papers = json.load(f)
            for paper in papers:
                row = {
                    "id": "W" + str(paper["id"]),
                    "year": year,
                    "conventionality": paper["referenced_works_uzzi"]["score"]["conventionality"],
                    "novelty": paper["referenced_works_uzzi"]["score"]["novelty"]
                }
                if not (math.isnan(row["conventionality"]) and math.isnan(row["novelty"])):
                    data.append(row)

    df = pd.DataFrame(data)

    df = df.sort_values(by="year")

    print(df.shape)
    print(df.head())
    #df.to_csv("uzzi_results.csv", index=False)
    plt.figure(figsize=(10, 6))

    # Plot novelty vs year
    sns.scatterplot(x='year', y='novelty', data=df, label='Novelty', color='blue', s=100)

    # Plot conventionality vs year
    sns.scatterplot(x='year', y='conventionality', data=df, label='Conventionality', color='red', s=100)

    # Add titles and labels
    plt.title("Novelty and Conventionality over Time", fontsize=16)
    plt.xlabel("Year", fontsize=14)
    plt.ylabel("Value", fontsize=14)

    # Show the legend
    plt.legend(title="Metrics")

    # Display the plot
    plt.show()

def read_foster_results():
    path_to_json = "Result/foster/referenced_works/"
    json_files = [pos_json for pos_json in os.listdir(path_to_json) if pos_json.endswith('.json')]

    data = []

    for file in json_files:
        year = int(file.replace(".json", "")) # remove the .json from the filename to get the year
        filepath = os.path.join(path_to_json, file)
        with open(filepath, "r") as f:
            papers = json.load(f)
            for paper in papers:
                row = {
                    "id": "W" + str(paper["id"]),
                    "year": year,
                    "novelty": paper["referenced_works_foster"]["score"]["novelty"]
                }
                if not math.isnan(row["novelty"]):
                    data.append(row)

    df = pd.DataFrame(data)

    df = df.sort_values(by="year")

    print(df.shape)
    print(df.head())
    #df.to_csv("foster_results.csv", index=False) 
    # Create the plot

# Defining main function
def main():
    read_uzzi_results()
    read_foster_results()

if __name__=="__main__":
    main()