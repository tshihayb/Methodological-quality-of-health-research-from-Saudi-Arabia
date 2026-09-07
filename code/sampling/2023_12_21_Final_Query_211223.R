# NOTE (public repository): the sampling seed is withheld. With the query
# above it would regenerate the drawn PMIDs, so it is a re-identification
# key rather than a reproducibility parameter. The realised sample is
# published as data; see the Data Availability statement.
# Install and load necessary packages
library(rentrez)
library(xml2)
library(dplyr)

#EXTRACT 5000 RANDOM ARTICLES AS STUDY SAMPLE

# Define the search query
Sample_query <- "(2022/01/01:2022/12/31[pdat]) AND (Saudi Arabia[Affiliation] OR Saudi Arabia[MeSH]) NOT (Systematic Review[Publication Type] OR systematic review[Publication Type] OR Review[Publication Type] OR Case Reports[Publication Type] OR Meta-Analysis[Publication Type] OR Preclinical Trial[Publication Type] OR Editorial[Publication Type] OR Letter[Publication Type] OR Comment[Publication Type] OR News[Publication Type] OR Patient Education Handout[Publication Type] OR Clinical Conference[Publication Type] OR Retracted Publication[Publication Type] OR systematic review[tiab] OR case study[tiab] OR in vitro[tiab] OR Systematic Reviews[tiab] OR Review[tiab] OR Case Reports[tiab] OR Case Report[tiab] OR Meta-Analysis[tiab] OR Editorial[tiab] OR Letter[tiab] OR Comment[tiab] OR News[tiab] OR Patient Education Handout[tiab] OR Clinical Conference[tiab] OR Retracted Publication[tiab]) AND (humans[Filter])"
# Search PubMed and get the count of matching articles
search_results <- entrez_search(db="pubmed", term=Sample_query)
total_articles <- search_results$count

# Print total number of articles that match the search criteria
print(paste("Total articles identified:", total_articles))


# Search PubMed and fetch IDs
search_results <- entrez_search(db="pubmed", term=Sample_query, retmax=total_articles)
ids <- search_results$ids
set.seed(SAMPLING_SEED)  # value withheld: the seed plus the query would regenerate the sampled PMIDs
# Generate a random number for each ID
random_numbers <- runif(length(ids))
# Order the IDs based on the random numbers
shuffled_ids <- ids[order(random_numbers)]
# select a random 1000 PMIDs
ids <- sample(shuffled_ids, 1000)

# Modify the function to return the specified details
get_article_details <- function(record_xml) {
  doc <- read_xml(record_xml)
  
  # Extracting data from XML
  title <- xml_text(xml_find_first(doc, "//ArticleTitle"))
  authors <- sapply(xml_find_all(doc, "//AuthorList/Author/LastName"), xml_text)
  pub_date <- paste(xml_text(xml_find_first(doc, "//PubDate/Year")), 
                    xml_text(xml_find_first(doc, "//PubDate/Month")), 
                    xml_text(xml_find_first(doc, "//PubDate/Day")), sep="-")
  journal <- xml_text(xml_find_first(doc, "//Journal/Title"))
  abstract <- xml_text(xml_find_first(doc, "//AbstractText"))
  affiliations <- sapply(xml_find_all(doc, "//AffiliationInfo/Affiliation"), xml_text)
  article_type <- xml_text(xml_find_first(doc, "//PublicationType"))
  pmid <- xml_text(xml_find_first(doc, "//PMID"))
  grants <- sapply(xml_find_all(doc, "//Grant/GrantID"), xml_text)
  grant_agencies <- sapply(xml_find_all(doc, "//Grant/Agency"), xml_text)
  
  # Construct the link for the study
  link <- paste0("https://pubmed.ncbi.nlm.nih.gov/", pmid, "/")
  
  # Combining authors and affiliations into strings
  authors <- paste(authors, collapse=", ")
  affiliations <- paste(affiliations, collapse="; ")
  grants <- paste(grants, collapse=", ")
  grant_agencies <- paste(grant_agencies, collapse=", ")
  
  return(list(Title=title, Authors=authors, PublicationDate=pub_date, Journal=journal,
              Abstract=abstract, Affiliations=affiliations, ArticleType=article_type,
              PMID=pmid, Grants=grants, GrantAgencies=grant_agencies, link = link))
}

# Create a data frame to store details
article_data <- data.frame(ID=character(), Title=character(), Authors=character(),
                           PublicationDate=character(), Journal=character(), Abstract=character(),
                           Affiliations=character(), ArticleType=character(), PMID=character(),
                           Grants=character(), GrantAgencies=character(), link=character(), stringsAsFactors=FALSE)

for (id in ids) {
  record <- entrez_fetch(db="pubmed", id=id, rettype="xml")
  details <- get_article_details(record)
  
  article_data <- rbind(article_data, data.frame(ID=id, 
                                                 Title=details$Title, 
                                                 Authors=details$Authors,
                                                 PublicationDate=details$PublicationDate,
                                                 Journal=details$Journal,
                                                 Abstract=details$Abstract,
                                                 Affiliations=details$Affiliations,
                                                 ArticleType=details$ArticleType,
                                                 PMID=details$PMID,
                                                 Grants=details$Grants,
                                                 GrantAgencies=details$GrantAgencies,
                                                 link=details$link))
  
  # Pause for 0.5 seconds to avoid hitting API rate limits
  Sys.sleep(0.5)
}

openxlsx::write.xlsx(article_data, "/Users/[USER]/Downloads/study_sample.xlsx")
