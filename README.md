# South Pole coding tasks
Laszlo Csunderlik

# How to Run the Script using Docker

This guide provides step-by-step instructions on how to build and run the script using Docker.

## Prerequisites

- Docker installed on your system.
- You need to create your own service account from Earth Engine and save it in src folder. 
See: https://github.com/laszlocsunderlik/south-pole-csl/blob/master/earth-engine-config-auth-example.json
Follow this link: https://developers.google.com/earth-engine/guides/service_account

## Building the Docker Image

1. Clone the repository to your local machine.
2. Navigate to the directory containing the Dockerfile and the script.
3. Open a terminal and run the following command to build the Docker image: 
```
docker build -t "your_build_name" .
```

## Running the Script

Once the Docker image is built, you can run the script using the following command:
```
docker run -it --rm "your_build_name" python south-pole-tasks.py "arg1_value"
```

If you need help to understand the argument:
```
docker run -it --rm "your_build_name" python south-pole-tasks.py --help
```

