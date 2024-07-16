# Bhoonidhi Downloader

A Python CLI tool for searching and downloading satellite imagery from Bhoonidhi.

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

## Features

- Search for openly available satellite scenes from Bhoonidhi portal based on bounding box coordinates, date range, and satellite/sensor
- View search results in tabular format with metadata and quicklook images
- Select a scene to download from the search results

### Limitations

- Supports only bounding box-based search for scenes.
  - Future support for search based on point coordinates and shapefile is planned.
- Supports only scenes with direct download links
- Supports only Medium resolution scenes from Optical Satellite Sensors.
  - Planning to add support for other sensors in future.
- Direct downloads only work for images from recent past - upto a year or so depending on the area and sensor. To download scenes dated ealier than that, using the [Bhoonidhi Portal](https://bhoonidhi.nrsc.gov.in/bhoonidhi/index.html#) is recommended.
  - Planning to add support for interacting with carts by way of viewing, adding, deleting items in future. This will help with downloading older scenes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
