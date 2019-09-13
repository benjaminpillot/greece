# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
import multiprocessing as mp

from abc import ABCMeta, abstractmethod
from pandas import concat, Series, DataFrame
from numpy import sum as npsum
from numpy import transpose as nptranspose
from numpy import isnan as npisnan
from numpy import all as npall
from numpy import zeros as npzeros
from gistools.geometry import mask, explode
from gistools.layer import PolygonLayer, GeoLayer
from gistools.projections import proj4_from
from gistools.raster import RasterMap, DigitalElevationModel
from gistools.stats import ZonalStatistics
from utils.check import type_assert, check_type, check_type_in_collection
from utils.sys.timer import broadcast_event
from utils.toolset import split_list_into_chunks, flatten, chunks

from greece.rentools.exceptions import GeoModelError, RasterResourceMapError, PolygonMapError
from greece.rentools.tools import get_location_from_polygon_layer
from greece.solartools.radiation import generate_hourly_ghi_sequence, generate_daily_toa_sequence, \
    generate_daily_kc_sequence, generate_daily_clear_sky_sequence, generate_daily_kc_sequence_over_month

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'


class GeoModel(metaclass=ABCMeta):
    """ Abstract class for all implemented geographic models

    Implement generic methods and attributes
    required for geographic models
    """
    _crs = None
    _surface_crs = None

    _cpu_count = None

    def __init__(self, *args, **kwargs):
        pass

    @property
    def crs(self):
        return self._crs

    @property
    def surface_crs(self):
        return self._surface_crs

    @property
    def cpu_count(self):
        return self._cpu_count

    @crs.setter
    def crs(self, crs):
        try:
            self._crs = proj4_from(crs)
        except ValueError:
            raise GeoModelError("Invalid CRS")

    @surface_crs.setter
    def surface_crs(self, crs):
        try:
            self._surface_crs = proj4_from(crs)
        except ValueError:
            raise GeoModelError("Invalid CRS")

    @cpu_count.setter
    def cpu_count(self, cpu_count):
        try:
            pool = mp.Pool(cpu_count)
            self._cpu_count = cpu_count
        except (TypeError, ValueError):
            raise GeoModelError("Invalid CPU count value")
        else:
            pool.close()


class PolygonMap(GeoModel):
    """ Abstract class for all relative polygon mapping

    Toolset for suitable sites, distance from specific
    locations, etc. Uses GeoLayer instance classes.
    Generate list of suitable polygons for further
    integration in optimisation model
    """

    polygons = None

    def __init__(self, base_layer, crs, dem, land_use, surface_crs=None, compute_distance_from_centroid=False,
                 cpu_count=1):
        """ Class constructor

        :param base_layer:
        :param crs: Main coordinate reference system
        :param dem: DigitalElevationModel object
        :param land_use: land use polygon layer
        :param surface_crs: CRS used for surface computation
        :param compute_distance_from_centroid: should distances be calculated from polygon centroids ? (true, false)
        :param cpu_count: number of cpu cores to use
        """

        super().__init__()

        self.crs = crs
        self.base_layer = base_layer
        self.dem = dem
        self.land_use = land_use

        if surface_crs is None:
            self.surface_crs = crs
        else:
            self.surface_crs = surface_crs

        self.compute_distance_from_centroid = compute_distance_from_centroid
        self.cpu_count = cpu_count
        self._distance_threshold = []
        self._layer_mask = []
        self._distance_to_polygon = []

    def _add_layer_list(self, attr_name, *args):

        if len(args) % 2 == 0:
            for layer, value in zip(args[::2], args[1::2]):
                check_type(value, (int, float))
                try:
                    layer = layer.to_crs(self.crs)
                except AttributeError:
                    raise PolygonMapError("layer must be a GeoLayer but is '%s'" % type(layer))
                self.__getattribute__(attr_name).extend([layer, value])
        else:
            raise PolygonMapError("Wrong number of input arguments")

    @broadcast_event("Computing distance from layer to polygon")
    def _get_distance_from_layer_to_polygon(self):
        """ Compute minimum distance from given layer(s) to polygons

        :return:
        """
        for layer in self._distance_to_polygon:
            self.polygons["distance to %s" % layer.name] = self.distance_polygons.distance(layer)

    @broadcast_event("Computing mask (may take a while...)")
    def _compute_mask(self, fast_intersection_surface):
        """ Compute mask

        :param fast_intersection_surface:
        :return:
        """
        if self._layer_mask:
            # Get all geometries corresponding to the mask
            mask_ = concat([layer.buffer(buffer_dist).geometry for layer, buffer_dist in zip(self._layer_mask[::2],
                                                                                             self._layer_mask[1::2])],
                           ignore_index=True)
            resource_polygons = mask(self.base_layer.geometry, mask_, fast_intersection_surface)
        else:
            resource_polygons = self.base_layer.geometry

        # Ensure no multipolygons
        resource_polygons = explode(resource_polygons)

        # Build layer of resource polygons (and clean invalid geometries)
        self.polygons = PolygonLayer.from_gpd(geometry=resource_polygons, crs=self.crs)

    @broadcast_event("Deleting small polygons")
    def _delete_small_polygons(self, min_polygon_surface):
        """ Delete polygons with respect to surface threshold

        :return:
        """
        self.polygons = self.polygons[self.equal_area_projection_polygons.area >= min_polygon_surface]

    @broadcast_event("Applying distance threshold")
    def _keep_polygons_within_distance(self):
        """ Keep polygons within threshold

        We use here a generator sorted by layer length in order to
        compute distance to the minimum number of geometry objects
        at every loop. Also, we reduce the size of the polygon set
        each time. It makes the computation very fast, even for very
        large sets.
        :return:
        """
        gen = (m for m in sorted(zip(self._distance_threshold[::2], self._distance_threshold[1::2]), key=lambda
               pair: len(pair[0])))
        for layer, distance_threshold in gen:
            distance = self.distance_polygons.distance(layer) <= distance_threshold
            self.polygons = self.polygons[distance]

    @broadcast_event("Splitting large polygons")
    def _split_large_polygons(self, split_surface_threshold, split_method, split_shape, **partition_options):
        """ Split large polygons with respect to threshold

        :param split_surface_threshold: surface threshold for split
        :param split_method: 'simple' or 'partition'
        :param partition_options: corresponding options when split_method == "partition"
        :return:
        """
        if split_shape == 'square':
            method = "katana_centroid"
        else:
            method = "hexana"

        if split_method == 'simple':
            self.polygons = self.equal_area_projection_polygons.split(
                split_surface_threshold, method=method, no_multipart=True).to_crs(self.crs)
        elif split_method == 'partition':
            self.polygons = \
                self.equal_area_projection_polygons.partition(split_surface_threshold, split_method=method,
                                                              **partition_options).to_crs(self.crs)

    @broadcast_event("Retrieving land use")
    def _get_land_use_in_polygon(self, land_use_attribute):
        """ Retrieve land use fractional area within polygons

        :return:
        """

        land_use = self.polygons.attr_area(self.land_use, land_use_attribute, normalized=True)
        land_use = {attr: land_use[attr] for attr in land_use.keys() if npsum(land_use[attr]) != 0}
        for key in land_use.keys():
            self.polygons[key] = land_use[key]

    @broadcast_event("Computing DEM statistics")
    def _get_dem_stats_in_polygon(self):
        """ Get DEM statistics within polygons

        Compute slope, elevation and aspect statistics (mean, std)
        :return:
        """
        slope = self.dem.compute_slope()
        aspect = self.dem.compute_aspect()

        for key, value in zip(["Elevation", "Slope", "Aspect"], [self.dem, slope, aspect]):
            zonal_stat = ZonalStatistics(value, self.polygons, is_surface_weighted=False, all_touched=True)
            self.polygons["%s mean" % key] = zonal_stat.mean()
            self.polygons["%s std" % key] = zonal_stat.std()

    @broadcast_event("Computing shape factor")
    def _get_shape_of_polygon(self, use_convex_hull):
        """ Get shape (circularity) of polygon

        :param use_convex_hull: bool
        :return:
        """
        self.polygons["shape_factor"] = self.polygons.shape_factor(use_convex_hull)

    def add_distance_to_polygon(self, *args):
        """ Add list of layers for which distance to
        resource must be computed

        :param args:
        :return:
        """
        for n, layer in enumerate(args):
            try:
                layer = layer.to_crs(self.crs)
            except AttributeError:
                raise PolygonMapError("input %d must be a GeoLayer but is '%s'" % (n, type(layer)))
            self._distance_to_polygon.append(layer)

    def add_layer_distance_threshold(self, *args):
        """ Add distance threshold for resource

        Add distance threshold from resource to specific layer
        over which corresponding polygons should be excluded
        :param args: (GeoLayer, distance threshold) arg list
        :return:
        """
        self._add_layer_list("_distance_threshold", *args)

    def add_layer_mask(self, *args):
        """ Add geo layers to resource mask

        Add geo layers which mask resource (such as
        "protected" areas where the resource cannot
        be exploited)
        :param args: (GeoLayer, buffer distance) arg list
        :return:

        :Example:
            >>> obj = RasterResourceMap(RasterMap("path/to/resource/raster"), GeoLayer("path/to/layer"))
            >>> obj.add_layer_mask(GeoLayer("path/to/mask"), 20, GeoLayer("path/to/mask2"), 50)
        """
        self._add_layer_list("_layer_mask", *args)

    def extract_polygons(self, fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                         split_shape, partition_options, compute_shape_factor, use_convex_hull, extract_land_use,
                         land_use_attribute, compute_dem_statistics, *args, **kwargs):
        """ Get resource polygons

        Retrieve polygons from layers, mask, distance
        threshold and corresponding resource within
        :param fast_intersection_surface:
        :param min_polygon_surface:
        :param max_polygon_surface:
        :param split_method: method used to split polygons ("simple" or "partition")
        :param split_shape: shape of sliced polygons ("square" or "hexagon")
        :param partition_options: dict of partition options
        :param compute_shape_factor: should we compute shape of polygons ? (bool)
        :param use_convex_hull: bool
        :param extract_land_use: bool
        :param land_use_attribute: attribute name in land use layer
        :param compute_dem_statistics: bool
        :return:
        """

        # Compute mask (longest part)
        self._compute_mask(fast_intersection_surface)

        # Clean geometry
        self.polygons = self.polygons.clean_geometry(delete_invalid=True)

        # Split with respect to surface threshold
        if max_polygon_surface is not None:
            self._split_large_polygons(max_polygon_surface, split_method, split_shape, **partition_options)

        # Delete too small polygons
        if min_polygon_surface > 0:
            self._delete_small_polygons(min_polygon_surface)

        # Keep polygons within distance threshold
        if self._distance_threshold:
            self._keep_polygons_within_distance()

        # Add area to layer
        self.polygons["area"] = self.equal_area_projection_polygons.area

        # Add distance from given layer to resource if necessary
        if self._distance_to_polygon:
            self._get_distance_from_layer_to_polygon()

        if compute_shape_factor:
            self._get_shape_of_polygon(use_convex_hull)

        if extract_land_use:
            self._get_land_use_in_polygon(land_use_attribute)

        if compute_dem_statistics:
            self._get_dem_stats_in_polygon()

    @property
    def dem(self):
        return self._dem

    @property
    def land_use(self):
        return self._land_use

    @property
    def base_layer(self):
        return self._base_layer

    @property
    def distance_polygons(self):
        if self.compute_distance_from_centroid:
            return self.polygons.centroid()
        else:
            return self.polygons

    @property
    def equal_area_projection_polygons(self):
        return self.polygons.to_crs(self.surface_crs)

    @base_layer.setter
    @type_assert(base_layer=PolygonLayer)
    def base_layer(self, base_layer):

        # Reproject base layer onto MAP CRS
        self._base_layer = base_layer.to_crs(self.crs)

    @dem.setter
    @type_assert(dem=DigitalElevationModel)
    def dem(self, dem):
        self._dem = dem.to_crs(self.crs)

    @land_use.setter
    @type_assert(land_use=PolygonLayer)
    def land_use(self, land_use):
        self._land_use = land_use.to_crs(self.crs)


class ResourceMap(PolygonMap, metaclass=ABCMeta):
    """ Class for mapping resource

    Get resource and add it to PolygonMap
    """

    _polygon_resource = None
    _contour_zones = None

    def __init__(self, resource, *args, **kwargs):
        """ Class constructor

        :param resource: resource data
        :param args: see parent class
        :param kwargs:
        """

        super().__init__(*args, **kwargs)
        self.resource = resource

    @abstractmethod
    def _get_resource_in_polygon(self, *args, **kwargs):
        """ Get resource in polygons

        :return:
        """
        pass

    @abstractmethod
    def _generate_resource_in_polygon(self, resource, generator, which_zone, *args, **kwargs):
        """ Use resource generator

        :return:
        """
        pass

    @abstractmethod
    def _get_resource_zones(self, *args, **kwargs):
        """ Get contour zones in resource map

        :param args:
        :param kwargs:
        :return:
        """
        pass

    def extract_polygons(self, fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                         split_shape, partition_options, compute_shape_factor, use_convex_hull, extract_land_use,
                         land_use_attribute, compute_dem_statistics, get_resource_options=None,
                         identify_resource_contour_zones=False, contour_options=None, use_resource_generator=False,
                         resource_generator=None, resource_generator_parameters=None, *args, **kwargs):

        super().extract_polygons(fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                                 split_shape, partition_options, compute_shape_factor, use_convex_hull,
                                 extract_land_use, land_use_attribute, compute_dem_statistics)

        # Retrieve resource in polygon
        resource = self._get_resource_in_polygon(**get_resource_options)

        # Drop polygons where resource is merely NaN
        index_na = [n for n, r in enumerate(resource) if npall(npisnan(r))]
        if index_na:
            resource = [r for n, r in enumerate(resource) if n not in index_na]
            self.polygons = self.polygons.drop(index=index_na)

        # Get resource zones if necessary
        if identify_resource_contour_zones:
            self._get_resource_zones(**contour_options)
            # zone = affect_zone_to_polygon(which_zone, self.polygons)
            # for n in range(zone.shape[1]):
            #     self.polygons["Contour %d" % (n+1)] = ["Zone %d" % z for z in zone[:, n]]

        # Generate resource if necessary
        if use_resource_generator:
            resource = self._generate_resource_in_polygon(resource, resource_generator, **resource_generator_parameters)

        # Write to attribute table
        self._polygon_resource = DataFrame({"polygon %d" % (n + 1): r for n, r in enumerate(resource)})

    # Must be overridden in sub-classes
    @property
    @abstractmethod
    def resource(self):
        return self._resource

    @resource.setter
    @abstractmethod
    def resource(self, resource):
        self._resource = resource

    @property
    def polygon_resource(self):
        return self._polygon_resource


class LayerResourceMap(ResourceMap):
    """ Class for mapping resource from layer

    Get resource from layer and add it to
    PolygonMap class
    """

    def _get_resource_in_polygon(self, *args, **kwargs):
        pass

    def _generate_resource_in_polygon(self, *args, **kwargs):
        pass

    def _get_resource_zones(self, *args, **kwargs):
        pass

    @property
    def resource(self):
        return self._resource


class RasterResourceMap(ResourceMap):
    """ Class for mapping resource from raster

    Get resource from raster and add it to
    PolygonMap class
    """

    def _generate_resource_in_polygon(self, *args, **kwargs):
        pass

    @broadcast_event("Identifying resource contour zones")
    def _get_resource_zones(self, contour_interval, contour_interval_type, main_percentile_range,
                            field_name="res_zone"):
        """ Get zones from resource contour

        :param contour_interval:
        :param main_percentile_range:
        :return:
        """
        abs_interval = False
        if contour_interval_type == "absolute":
            abs_interval = True

        self._contour_zones = \
            [resource.contour(contour_interval, abs_interval, (100 - main_percentile_range)/2, 100 -
             (100 - main_percentile_range)/2).polygonize(field_name).to_crs(self.crs).dissolve(by=field_name) for
             resource in self.resource]
        # [resource.contour(contour_interval, abs_interval, (100 - main_percentile_range)/2, 100 -
        #  (100 - main_percentile_range)/2).polygonize(field_name).to_crs(self.crs).singlepart_to_multipart(
        #     field_name) for resource in self.resource]

    @broadcast_event("Extracting resource from raster")
    def _get_resource_in_polygon(self, is_surface_weighted, all_touched):
        """ Get resource in polygons

        :return:
        """
        mean = ZonalStatistics(self.resource, self.polygons, is_surface_weighted, all_touched).mean()

        return nptranspose(mean)

    def extract_polygons(self, fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                         split_shape, partition_options, compute_shape_factor, use_convex_hull, extract_land_use,
                         land_use_attribute, compute_dem_statistics, is_surface_weighted=False, all_touched=True,
                         identify_resource_contour_zones=False, contour_interval_type=None, contour_interval=None,
                         main_percentile_range=None, use_resource_generator=False, resource_generator=None,
                         resource_generator_parameters=None, *args, **kwargs):
        """ Get resource polygons

        Retrieve polygons from layers, mask, distance
        threshold and corresponding resource within
        :return:
        """

        get_resource_options = dict(is_surface_weighted=is_surface_weighted, all_touched=all_touched)
        contour_options = dict(contour_interval_type=contour_interval_type, contour_interval=contour_interval,
                               main_percentile_range=main_percentile_range)

        super().extract_polygons(fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                                 split_shape, partition_options, compute_shape_factor, use_convex_hull,
                                 extract_land_use, land_use_attribute, compute_dem_statistics, get_resource_options,
                                 identify_resource_contour_zones, contour_options, use_resource_generator,
                                 resource_generator, resource_generator_parameters)

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, resource):
        try:
            check_type(resource, RasterMap)
            resource = [resource]
        except TypeError:
            try:
                check_type_in_collection(resource, RasterMap)
            except TypeError:
                raise RasterResourceMapError("Input must be a RasterMap or a list of RasterMap but is '%s'" % type(
                    resource))
        self._resource = resource


class SolarGHIResourceMap(RasterResourceMap):
    """ Class for mapping solar GHI

    """

    @broadcast_event("Generating GHI time series")
    def _generate_resource_in_polygon(self, resource, generator, time_zone, accuracy, base_year, kc_tolerance,
                                      ghi_tolerance):
        """ Generate downscale resource in polygon according to global average resource

        :param resource: output from _get_resource_in_polygon
        :param generator: type of generator ("daily", "hourly", etc.)
        :param time_zone: valid pytz time zone
        :param accuracy: time resolution for integrating over toa radiation
        :param base_year: base year used in all solar computations
        :param kc_tolerance: tolerance when generating daily kc
        :param ghi_tolerance: relative tolerance for resulting hourly GHI
        :return: list of list of GHI values and time step format
        """
        def location_chunks():
            return chunks(location, self.cpu_count)

        def ghi_chunks():
            return chunks(resource, self.cpu_count)

        def which_zone_chunks():
            return chunks(which_zone, self.cpu_count)

        # Retrieve location from polygons in layer
        location = get_location_from_polygon_layer(self.polygons, "Elevation mean", time_zone)

        # daily_clear_sky_radiation = [generate_daily_clear_sky_sequence(loc, accuracy, base_year) for loc in location]

        # Parallelization
        pool = mp.Pool(self.cpu_count)

        daily_clear_sky_radiation = pool.map(mp_generate_daily_clear_sky_sequence, [[loc, accuracy, base_year] for
                                                                                    loc in location_chunks()])
        daily_toa_radiation = pool.map(mp_generate_daily_toa_sequence, [[loc, accuracy, base_year] for
                                                                        loc in location_chunks()])

        # daily_toa_radiation = [generate_daily_toa_sequence(loc, accuracy, base_year) for loc in location]

        # If data are monthly, generate daily
        if generator == "daily" or generator == "daily_and_hourly":

            kcm = pool.map(mp_compute_monthly_kc, [[cls, ghi] for cls, ghi
                                                   in zip(daily_clear_sky_radiation, ghi_chunks())])
            # kcm = [[ghi[m - 1] / npsum(cls[cls.index.month == m])
            #         for m in range(1, 13)] for cls, ghi in zip(daily_clear_sky_radiation, resource)]

            if self._contour_zones is not None:
                which_zone = [[arg[0] for arg in contour_zone.intersecting_features(self.polygons.centroid())] for
                              contour_zone in self._contour_zones]

                # daily_kc = [pool.apply(generate_kc_serie_by_zone,
                #                        args=(zone, kc, base_year, time_zone, kc_tolerance))
                #             for zone, kc in zip(which_zone_chunks(), flatten(kcm))]
                daily_kc = generate_kc_serie_by_zone(which_zone, flatten(kcm), base_year, time_zone, kc_tolerance)
                daily_kc = split_list_into_chunks(daily_kc, self.cpu_count)
            else:
                daily_kc = pool.map(mp_generate_daily_kc_sequence, [[kc, base_year, time_zone, kc_tolerance] for kc
                                                                    in kcm])
                # daily_kc = [generate_daily_kc_sequence(kc, base_year, time_zone, kc_tolerance) for kc in kcm]

            daily_kt = pool.map(mp_compute_daily_kt_sequence_from_kc, [[kc, cls, toa] for kc, cls, toa in zip(
                daily_kc, daily_clear_sky_radiation, daily_toa_radiation)])
            # daily_kt = [kc * cls / toa for kc, cls, toa in zip(daily_kc, daily_clear_sky_radiation, daily_toa_radiation)]

        else:
            daily_kt = pool.map(mp_compute_daily_kt_sequence_from_ghi, [[ghi, toa] for ghi, toa in
                                                                        zip(ghi_chunks(), daily_toa_radiation)])
            daily_kc = pool.map(mp_compute_daily_kc_sequence, [[kt, toa, cls] for kt, cls, toa in zip(
                daily_kt, daily_toa_radiation, daily_clear_sky_radiation)])
            # daily_kt = [Series(data=ghi, index=toa.index)/toa for ghi, toa in zip(resource, daily_toa_radiation)]
            # daily_kc = [kt * toa / cls for kt, toa, cls in zip(daily_kt, daily_toa_radiation, daily_clear_sky_radiation)]

        # If data are daily, generate hourly
        if generator == "daily_and_hourly" or generator == "hourly":
            ghi = flatten(pool.map(mp_generate_hourly_ghi_sequence,
                                   [[kt, kc, toa, loc, accuracy, base_year, ghi_tolerance] for kt, kc, toa, loc in
                                    zip(daily_kt, daily_kc, daily_toa_radiation, location_chunks())]))
            # ghi = [generate_hourly_ghi_sequence(kt, kc, toa, loc, accuracy, base_year, ghi_tolerance)
            #        for kt, kc, toa, loc in zip(daily_kt, daily_kc, daily_toa_radiation, location)]
        else:
            ghi = flatten(pool.map(mp_compute_daily_ghi_sequence, [[kt, toa] for kt, toa in zip(daily_kt,
                                                                                                daily_toa_radiation)]))
            # ghi = [kt * toa for kt, toa in zip(daily_kt, daily_toa_radiation)]

        # Close multiprocessing
        pool.close()

        return ghi

    def _get_resource_zones(self, contour_interval, contour_interval_type, main_percentile_range,
                            field_name="ghi_zone"):
        return super()._get_resource_zones(contour_interval, contour_interval_type, main_percentile_range,
                                           field_name)

    def extract_polygons(self, fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                         split_shape, partition_options, compute_shape_factor, use_convex_hull, extract_land_use,
                         land_use_attribute, compute_dem_statistics, is_surface_weighted=False, all_touched=True,
                         identify_resource_contour_zones=False, contour_interval_type="absolute", contour_interval=4000,
                         main_percentile_range=96, use_resource_generator=False, resource_generator=None,
                         time_zone='UTC', accuracy="30 min", base_year=2018, daily_kc_tolerance=0.02,
                         hourly_ghi_tolerance=0.05, *args, **kwargs):

        resource_generator_parameters = dict(time_zone=time_zone, accuracy=accuracy, base_year=base_year,
                                             kc_tolerance=daily_kc_tolerance, ghi_tolerance=hourly_ghi_tolerance)

        super().extract_polygons(fast_intersection_surface, min_polygon_surface, max_polygon_surface, split_method,
                                 split_shape, partition_options, compute_shape_factor, use_convex_hull,
                                 extract_land_use, land_use_attribute, compute_dem_statistics, is_surface_weighted,
                                 all_touched, identify_resource_contour_zones, contour_interval_type, contour_interval,
                                 main_percentile_range, use_resource_generator, resource_generator,
                                 resource_generator_parameters)


@type_assert(layer=PolygonLayer, raster=RasterMap)
def get_resource_within_layer_of_polygons(layer, raster, is_surface_weighted=True, all_touched=False):
    """ Get resource from raster within polygons of layer

    :param layer: GeoLayer instance
    :param raster: RasterMap instance
    :param is_surface_weighted: bool
    :param all_touched: rasterization type
    :return: list of resource values
    """
    zonal_stat = ZonalStatistics(raster, layer, is_surface_weighted=is_surface_weighted, all_touched=all_touched)

    return zonal_stat.mean()


def generate_kc_serie_by_zone(which_zone, kcm, base_year, time_zone, tolerance):
    """ Generate serie of random number for each resource zone

    :param which_zone:
    :param kcm: monthly mean clear-sky indices for each polygons
    :param base_year:
    :param time_zone: corresponding time zone
    :param tolerance: tolerance around kc_main distribution mean from original kcm_main value
    :return:
    """
    kc = [Series() for _ in range(len(kcm))]

    for mth, mth_list in enumerate(which_zone):
        for zone in mth_list:
            if zone:
                _kcm = [kcm[z][mth] for z in zone]
                kc_series = generate_daily_kc_sequence_over_month(_kcm, _kcm, mth + 1, base_year, time_zone, tolerance)
                for idx, series in zip(zone, kc_series):
                    kc[idx] = kc[idx].append(series)

    return kc


def affect_zone_to_polygon(which_zone, polygons):
    """ Affect a resource zone to PolygonLayer of polygons

    :param which_zone:
    :param polygons:
    :return:
    """
    zone = npzeros((len(polygons), len(which_zone)), dtype=int)
    for n, t_unit in enumerate(which_zone):
        k = 0
        for _zone in t_unit:
            if _zone:
                k += 1
                for idx in _zone:
                    zone[idx][n] = k

    return zone


# Parallelized function (MP prefix for MultiProcessing)
def mp_compute_monthly_kc(argmap):
    """ Compute monthly clear-sky index

    """
    clear_sky_radiation, global_horizontal_irradiance = argmap
    return [[ghi[m - 1] / npsum(cls[cls.index.month == m]) for m in range(1, 13)]
            for cls, ghi in zip(clear_sky_radiation, global_horizontal_irradiance)]


def mp_compute_daily_kt_sequence_from_kc(argmap):
    """ Compute daily clearness index sequence from daily clear-sky index

    """
    clear_sky_index, clear_sky_radiation, toa_radiation = argmap
    return [kc * cls / toa for kc, cls, toa in zip(clear_sky_index, clear_sky_radiation, toa_radiation)]


def mp_compute_daily_kt_sequence_from_ghi(argmap):
    """ Compute daily clearness index sequence from GHI

    """
    global_horizontal_irradiance, toa_radiation = argmap
    return [Series(data=ghi, index=toa.index) / toa for ghi, toa in zip(global_horizontal_irradiance, toa_radiation)]


def mp_compute_daily_ghi_sequence(argmap):
    """ Compute daily GHI sequence

    """
    clearness_index, toa_radiation = argmap
    return [kt * toa for kt, toa in zip(clearness_index, toa_radiation)]


def mp_compute_daily_kc_sequence(argmap):
    """ Compute daily clear-sky index sequence

    """
    clearness_index, toa_radiation, clear_sky_radiation = argmap
    return [kt * toa / cls for kt, toa, cls in zip(clearness_index, toa_radiation, clear_sky_radiation)]


def mp_generate_daily_kc_sequence(argmap):
    """ Generate daily clear-sky index sequence

    :param argmap:
    :return:
    """
    monthly_clear_sky_index, base_year, time_zone, kc_tolerance = argmap
    return [generate_daily_kc_sequence(kc, base_year, time_zone, kc_tolerance) for kc in monthly_clear_sky_index]


def mp_generate_daily_clear_sky_sequence(argmap):
    """ Generate daily clear sky radiation sequence

    :param argmap:
    :return:
    """
    location, accuracy, base_year = argmap
    return [generate_daily_clear_sky_sequence(loc, accuracy, base_year) for loc in location]


def mp_generate_daily_toa_sequence(argmap):
    """ Generate daily TOA (Top of Atmosphere) radiation sequence

    :param argmap:
    :return:
    """
    location, accuracy, base_year = argmap
    return [generate_daily_toa_sequence(loc, accuracy, base_year) for loc in location]


def mp_generate_hourly_ghi_sequence(argmap):
    """ Generate hourly GHI sequence

    """
    clearness_index, clear_sky_index, toa_radiation, location, accuracy, base_year, ghi_tolerance = argmap
    return [generate_hourly_ghi_sequence(kt, kc, toa, loc, accuracy, base_year, ghi_tolerance)
            for kt, kc, toa, loc in zip(clearness_index, clear_sky_index, toa_radiation, location)]
