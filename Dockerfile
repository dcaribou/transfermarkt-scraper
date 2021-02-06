FROM continuumio/miniconda3

WORKDIR /app

# The code to run when container is started:
COPY tfmkt tfmkt
COPY scrapy.cfg .

# Create the environment:
COPY environment.yml .
RUN conda env create -f environment.yml

ENV PATH /opt/conda/envs/transfermarkt-scraper/bin:$PATH
RUN /bin/bash -c "source activate transfermarkt-scraper"
