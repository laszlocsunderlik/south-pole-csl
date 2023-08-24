FROM continuumio/miniconda3:23.3.1-0
RUN conda install --name base -c conda-forge mamba

# foundational build/publish dependencies
RUN mamba install -c conda-forge python-build

# occasionally changing dependencies
COPY environment.yml ./
RUN mamba env update --name base

# frequently changing source code
WORKDIR /app
# make a writable dir for numba to use... see https://github.com/numba/numba/issues/4032#issuecomment-547088606
RUN mkdir /numba_cache && chmod -R g+w /numba_cache
ENV NUMBA_CACHE_DIR=/numba_cache
#COPY ./setup.cfg ./
COPY ./src ./src

# default entrypoint to run the production artifact
ENTRYPOINT ["python", "south-pole-tasks"]