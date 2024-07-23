# Bhoonidhi Downloader

A Python CLI tool for searching and downloading satellite imagery from Bhoonidhi Browse & Order Portal.

## Installation

```shell
pip install bhoonidhi-downloader
```

## Usage

Basic usage:

**Authenticate**:

```shell
bhoonidhi-downloader authenticate <username> --password <password>
```

**Search Scenes using Bounding Box Coordinates**:

```shell
bhoonidhi-downloader search <minx> <maxx> <miny> <maxy> <start_date> <end_date> <satellite> <sensor>
```

Example - downloading a Sentinel-2A MSI scene from from December 2023 for Shillong, Meghalaya:

```shell
bhoonidhi-downloader search 91.77 92 25.496 25.695 2023-12-01 2023-12-30 Sentinel-2A MSI
```

For more information, use the `--help` option:

**Display Bhoonidhi Browse & Order Archive**:

```shell
bhoonidhi-downloader archive
```

The `archive` command displays a table that listing all available satellites and their corresponding sensors along with information about availability, spatial resolution, and access level. The information can be filtered by satellite and sensor using the `--sat` options.

Example - Displaying all available sensors and their information for ResourceSat-2 satellite:

```shell
bhoonidhi-downloader archive --sat ResourceSat-2
```

## Features

- Search for openly available satellite scenes from Bhoonidhi portal based on bounding box coordinates, date range, and satellite/sensor
- View search results in tabular format with metadata and quicklook images
- Download recent scenes that are available via direct download

![alt text](docs/image.png)

### Limitations

- Supports only bounding box-based search for scenes.
  - Future support for search based on point coordinates and shapefile is planned.
- Supports only scenes with direct download links
- Supports only Low and Medium resolution scenes from Optical and Microwave Satellite Sensors.
  - Planning to add support for other sensors in future.
- Direct downloads only work for images from recent past - upto a year or so depending on the area and sensor. To download scenes dated ealier than that, using the [Bhoonidhi Portal](https://bhoonidhi.nrsc.gov.in/bhoonidhi/index.html#) is recommended.
  - Planning to add support for interacting with carts by way of viewing, adding, deleting items in future. This will help with downloading older scenes.
