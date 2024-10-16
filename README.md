# PICNIC

## Run PICNIC in docker (easiest)

You need to have docker installed already, then you can download the docker
image and run it on your data. The major benefit of docker is that
Python, FSL, FreeSurfer, AFNI, Connectome Workbench, and PICNIC are
already installed inside the docker container, so you don't have to
deal with those dependencies on your own.

You can use a provided wrapper script for the simplest interface.

```bash
/path/to/picnic/scripts/run_picnic_in_docker \
  /path/to/input_deck.inp \
  /path/to/your/read_only_data \
  /path/to/your/writable_results
```

Or you can use docker directly for more control.

```bash
docker pull mfschmidt/picnic:latest
docker run --rm \
  -v /path/to/your/data:/input:ro \
  -v /path/to/your/results:/output:rw \
  -v /path/to/your/input_deck.inp:/input_deck.inp:ro \
  mfschmidt/picnic:latest /input_deck.inp
```

## Run PICNIC directly

To run picnic directly, you don't need docker, but you do need to have all of
its dependencies already installed.

```bash
pip install -U git+git@github.com:ehauser-mind/PICNIC.git
cd PICNIC
./src/picnic/run.py my_input_deck.inp
```
