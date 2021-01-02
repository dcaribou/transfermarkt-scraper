FROM continuumio/miniconda3

WORKDIR /app

# Create the environment:
COPY environment.yml .
RUN conda env create -f environment.yml

# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "transfermarkt-scraper", "/bin/bash", "-c"]

# The code to run when container is started:
COPY tfmkt tfmkt
COPY scrapy.cfg .

ENTRYPOINT ["conda", "run", "-n", "transfermarkt-scraper"]
