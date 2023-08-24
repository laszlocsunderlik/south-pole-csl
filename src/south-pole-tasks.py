import sys
import ee
from colorama import Fore

# Initialize Earth Engine
service_account_key_file = "south-pole-csl-396609-140ecba9262a.json"
ee.Initialize(ee.ServiceAccountCredentials(None, key_file=service_account_key_file))


def get_country_boundary(gaul_code: int) -> dict:
    """
    From Google Earth Engine using the FAO-GAUL dataset for national level boundaries. With the Gaul Country Code it
    returns the national boundaries in GeoJson.
    :param gaul_code:FAO Gaul Country Code.
    :return: National boundaries in GeoJson.
    """
    countries = ee.FeatureCollection("FAO/GAUL/2015/level0")
    print(Fore.WHITE + "Obtain Global Administrative Unit Layers 2015, Country Boundaries")
    country = countries.filter(ee.Filter.eq('ADM0_CODE', gaul_code))
    country_geom = country.geometry()
    return country_geom.getInfo()


def get_admin_units(gaul_code: int) -> dict:
    """
    From Google Earth Engine using the FAO-GAUL dataset for sub-national level boundaries. With the Gaul Country Code it
    returns the sub-national boundaries in GeoJson.
    :param gaul_code: FAO Gaul Country Code.
    :return: Sub-nation boundaries.
    """
    admin_units = ee.FeatureCollection("FAO/GAUL/2015/level1")
    print(Fore.WHITE + "Obtain Global Administrative Unit Layers 2015, First-Level Administrative Units")
    admin_unit = admin_units.filter(ee.Filter.eq("ADM0_CODE", gaul_code))
    country_geom = admin_unit.geometry()
    return country_geom.getInfo()


def get_hansen() -> ee.Image:
    """
    From Google Earth Engine returns the global Hansen dataset. Which is the results from time-series analysis of
    Landsat images in characterizing global forest extent and change.
    :return: Global Hansen dataset.
    """
    print(Fore.WHITE + "Obtain Hansen Global Forest Change v1.10 (2000-2022)")
    return ee.Image("UMD/hansen/global_forest_change_2022_v1_10")


def clip_raster_with_boundary(forest_change: ee.Image, country: dict) -> ee.Image:
    """
    Clip the Hansen dataset with national or sub-nation boundaries.
    :param forest_change: Global Hansen dataset.
    :param country: National or sub-national boundaries.
    :return: ee.Image object. The output bands correspond exactly to the input bands, except data not covered by the
    geometry is masked. The output image retains the metadata of the input image.
    """
    print(Fore.YELLOW + "Clip the Hansen dataset with boundaries")
    return forest_change.clip(country)


def stable_forest(image: ee.Image) -> None:
    """
    The function calculates the size (km²) of the area of stable forest between the year 2000 and the last year of
    available data. The first part selects the relevant bands for this calculation. The second part calculates the
    stable area based on the pixel area. Assume that the initial forest coverage encompasses pixels with a canopy cover
    of at least 10% in the treecover2000 layer.
    :param image: ee.Image for the area of interest.
    :return: None
    """
    hansen_select = (
        image.select("treecover2000").gt(10)
        .And(image.select("gain").eq(0))
        .And(image.select("loss").eq(0))
    )
    print(Fore.YELLOW + "Calculating stable forest area...")
    stable_forest_area = hansen_select.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        scale=30,
        maxPixels=1e13
    ).get("treecover2000")

    stable_forest_area_sqkm = ee.Number(stable_forest_area).divide(1e6)
    print(Fore.GREEN + "Stable forest area in (km²) between 2000 and 2022:", stable_forest_area_sqkm.getInfo())


def deforestation(image: ee.Image) -> None:
    """
    The function calculates the size (km²) of deforested regions in that final year compared to the year 2000.
    The first part selects the relevant bands for this calculation. The second part calculates the deforested area based
    on the pixel area. Assume that the initial forest coverage encompasses pixels with a canopy cover of at least 10% in
    the treecover2000 layer.
    :param image: ee.Image for the area of interest.
    :return: None
    """
    deforested_regions = (
        image.select("treecover2000").gt(10)
        .And(image.select("loss").eq(1))
    )
    print(Fore.YELLOW + "Calculating deforested regions...")
    deforested_area_m2 = deforested_regions.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        scale=30,
        maxPixels=1e13
    ).get("treecover2000")

    deforested_area_sqkm = ee.Number(deforested_area_m2).divide(1e6)
    print(Fore.GREEN + "Deforested area in (km²) between 2000 and 2022:", deforested_area_sqkm.getInfo())


def deforestation_rate(image: ee.Image, country: dict) -> None:
    """
    The function computes the deforestation rate and calculates the sum of forest loss for each year. The first section
    makes a band selection from the clipped Hansen dataset and calculates the unique years. The second section
    calculates the sum of forest loss for each year. The third part calculates the year loss rate based on the
    previous year.
    :param image: ee.Image for the area of interest.
    :return: dictionary for each year the sum of forest loss
    """
    # Select the loss year band
    lossyear_band = image.select('lossyear')

    # Get a list of unique years with forest loss
    unique_years = lossyear_band.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=country,
        scale=30,
        maxPixels=1e13
    ).get('lossyear')
    years = unique_years.getInfo()
    print(Fore.YELLOW + "Calculating deforestation rate...")
    sorted_unique_years = keys_integer(years)
    index_loss_sum = {}
    for year in sorted_unique_years:
        loss_mask = lossyear_band.eq(year)
        loss_for_year = loss_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=country,
            scale=30,
            maxPixels=1e13
        ).get('lossyear')
        index_loss_sum[year] = loss_for_year.getInfo()

    year_loss_sum = year_mapping(index_loss_sum)
    yearly_rate = rate_calc(year_loss_sum)

    print(Fore.GREEN + f"Deforestation rate based on previous year: {yearly_rate}")
    highest_key, highest_value = max(yearly_rate.items(), key=lambda x: x[1])
    print(Fore.GREEN + f"Highest rate is {highest_value} at {highest_key}")


def keys_integer(years: dict) -> dict:
    """
    Converts the year index from string to integer.
    :param years: year index as string.
    :return: year index as integer.
    """
    return {int(key): value for key, value in sorted(years.items(), key=lambda item: int(item[0]))}


def year_mapping(sorted_unique_years: dict) -> dict:
    """
    Maps to the year index to correct years.
    :param sorted_unique_years: Unique years as index
    :return: Unique years as correct year
    """
    new_keys_mapping = {1: 2000, 2: 2001, 3: 2003, 4: 2004, 5: 2005, 6: 2006, 7: 2007, 8: 2008, 9: 2009, 10: 2010,
                        11: 2011, 12: 2012, 13: 2013, 14: 2014, 15: 2015, 16: 2016, 17: 2017, 18: 2018, 19: 2019,
                        20: 2020, 21: 2021, 22: 2022}

    return {new_keys_mapping[key]: value for key, value in sorted_unique_years.items()}


def rate_calc(loss_dict: dict) -> dict:
    """
    Calculates the deforestation rate based on the previous year.
    :param loss_dict: dictionary for every year loss
    :return: dictionary rate based on the previous year
    """
    deforestation_rates = {}
    previous_value = None

    for year, value in sorted(loss_dict.items()):
        if previous_value is not None:
            rate = (value - previous_value) / previous_value
            deforestation_rates[year] = rate
        previous_value = value

    return deforestation_rates


def main(country_name: int) -> None:
    # Download country boundary and administrative units
    country_boundary = get_country_boundary(country_name)
    admin_units = get_admin_units(country_name)

    # Download Hasen dataset and clip to administrative boundary
    forest_change = get_hansen()
    clip = clip_raster_with_boundary(forest_change, country_boundary)

    # Stable forest calculation
    stable_forest(clip)

    # Deforestation calculation
    deforestation(clip)

    # Year loss rate
    deforestation_rate(clip, country_boundary)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] == "--help":
        print(Fore.BLUE + "Usage: python script_name.py <FAO Gaul Code>")
        print(Fore.BLUE + "Example: python south-pole-tasks.py 113")
        print(Fore.BLUE + "The FAO Gaul Code corresponds to the desired country.")
        sys.exit(1)

    country_name = int(sys.argv[1])
    main(country_name)
