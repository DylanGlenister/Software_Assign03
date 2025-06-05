from fastapi import APIRouter, Depends

from ..models.catalogue import Catalogue
from ..utils.settings import SETTINGS
from .database import Database, get_db

catalogue_route = APIRouter(
	prefix=SETTINGS.api_path +
	'/catalogue',
	tags=['catalogue']
)


@catalogue_route.post('/get_all')
def get_all_products_route():
	# Call Catalogue.get_all_products
	# return Catalogue._products
	pass
