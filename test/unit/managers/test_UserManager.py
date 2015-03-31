# -*- coding: utf-8 -*-
"""
"""
import sys
import os
import pprint
import unittest

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.insert( 1, __GALAXY_ROOT__ + 'lib' )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
from galaxy.util.bunch import Bunch

import mock
from test_ModelManager import BaseTestCase
from galaxy.managers import users
from galaxy.managers import histories


# =============================================================================
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )
user4_data = dict( email='user4@user4.user4', username='user4', password=default_password )


# =============================================================================
class UserManagerTestCase( BaseTestCase ):

    def test_framework( self ):
        self.log( "(for testing) should have admin_user, and admin_user is current" )
        self.assertEqual( self.trans.user, self.admin_user )

    def test_base( self ):
        self.log( "should be able to create a user" )
        user2 = self.user_mgr.create( self.trans, **user2_data )
        self.assertIsInstance( user2, model.User )
        self.assertIsNotNone( user2.id )
        self.assertEqual( user2.email, user2_data[ 'email' ] )
        self.assertEqual( user2.password, default_password )

        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to query" )
        users = self.trans.sa_session.query( model.User ).all()
        self.assertEqual( self.user_mgr.list( self.trans ), users )

        self.assertEqual( self.user_mgr.by_id( self.trans, user2.id ), user2 )
        self.assertEqual( self.user_mgr.by_ids( self.trans, [ user3.id, user2.id ] ), [ user3, user2 ] )

        self.log( "should be able to limit and offset" )
        self.assertEqual( self.user_mgr.list( self.trans, limit=1 ), users[0:1] )
        self.assertEqual( self.user_mgr.list( self.trans, offset=1 ), users[1:] )
        self.assertEqual( self.user_mgr.list( self.trans, limit=1, offset=1 ), users[1:2] )

        self.assertEqual( self.user_mgr.list( self.trans, limit=0 ), [] )
        self.assertEqual( self.user_mgr.list( self.trans, offset=3 ), [] )

        self.log( "should be able to order" )
        self.assertEqual( self.user_mgr.list( self.trans, order_by=( sqlalchemy.desc( model.User.create_time ) ) ),
            [ user3, user2, self.admin_user ] )

    def test_invalid_create( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )

        self.log( "emails must be unique" )
        self.assertRaises( exceptions.Conflict, self.user_mgr.create,
            self.trans, **dict( email='user2@user2.user2', username='user2a', password=default_password ) )
        self.log( "usernames must be unique" )
        self.assertRaises( exceptions.Conflict, self.user_mgr.create,
            self.trans, **dict( email='user2a@user2.user2', username='user2', password=default_password ) )

    def test_email_queries( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to query by email" )
        self.assertEqual( self.user_mgr.by_email( self.trans, user2_data[ 'email' ] ), user2 )

        #note: sorted by email alpha
        users = self.trans.sa_session.query( model.User ).all()
        self.assertEqual( self.user_mgr.by_email_like( self.trans, '%@%' ), [ self.admin_user, user2, user3 ] )

    def test_admin( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to test whether admin" )
        self.assertTrue( self.user_mgr.is_admin( self.trans, self.admin_user ) )
        self.assertFalse( self.user_mgr.is_admin( self.trans, user2 ) )
        self.assertEqual( self.user_mgr.admins( self.trans ), [ self.admin_user ] )
        self.assertRaises( exceptions.AdminRequiredException, self.user_mgr.error_unless_admin, self.trans, user2 )
        self.assertEqual( self.user_mgr.error_unless_admin( self.trans, self.admin_user ), self.admin_user )

    def test_anonymous( self ):
        anon = None
        user2 = self.user_mgr.create( self.trans, **user2_data )

        self.log( "should be able to tell if a user is anonymous" )
        self.assertRaises( exceptions.AuthenticationFailed, self.user_mgr.error_if_anonymous, self.trans, anon )
        self.assertEqual( self.user_mgr.error_if_anonymous( self.trans, user2 ), user2 )

    def test_current( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to tell if a user is the current (trans) user" )
        self.assertEqual( self.user_mgr.current_user( self.trans ), self.admin_user )
        self.assertNotEqual( self.user_mgr.current_user( self.trans ), user2 )

    def test_api_keys( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should return None if no APIKey has been created" )
        self.assertEqual( self.user_mgr.valid_api_key( self.trans, user2 ), None )

        self.log( "should be able to generate and retrieve valid api key" )
        user2_api_key = self.user_mgr.create_api_key( self.trans, user2 )
        self.assertIsInstance( user2_api_key, basestring )
        self.assertEqual( self.user_mgr.valid_api_key( self.trans, user2 ).key, user2_api_key )

        self.log( "should return the most recent (i.e. most valid) api key" )
        user2_api_key_2 = self.user_mgr.create_api_key( self.trans, user2 )
        self.assertEqual( self.user_mgr.valid_api_key( self.trans, user2 ).key, user2_api_key_2 )


# =============================================================================
class UserSerializerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( UserSerializerTestCase, self ).set_up_managers()
        self.user_serializer = users.UserSerializer( self.app )

    def test_views( self ):
        user = self.user_mgr.create( self.trans, **user2_data )

        self.log( 'should have a summary view' )
        summary_view = self.user_serializer.serialize_to_view( self.trans, user, view='summary' )
        self.assertKeys( summary_view, self.user_serializer.views[ 'summary' ] )

        self.log( 'should have the summary view as default view' )
        default_view = self.user_serializer.serialize_to_view( self.trans, user, default_view='summary' )
        self.assertKeys( summary_view, self.user_serializer.views[ 'summary' ] )

        self.log( 'should have a serializer for all serializable keys' )
        for key in self.user_serializer.serializable_keyset:
            instantiated_attribute = getattr( user, key, None )
            if not ( ( key in self.user_serializer.serializers )
                  or ( isinstance( instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS ) ) ):
                self.fail( 'no serializer for: %s (%s)' % ( key, instantiated_attribute ) )
        else:
            self.assertTrue( True, 'all serializable keys have a serializer' )

    def test_views_and_keys( self ):
        user = self.user_mgr.create( self.trans, **user2_data )

        self.log( 'should be able to use keys with views' )
        serialized = self.user_serializer.serialize_to_view( self.trans, user,
            view='summary', keys=[ 'create_time' ] )
        self.assertKeys( serialized,
            self.user_serializer.views[ 'summary' ] + [ 'create_time' ] )

        self.log( 'should be able to use keys on their own' )
        serialized = self.user_serializer.serialize_to_view( self.trans, user,
            keys=[ 'tags_used', 'is_admin' ] )
        self.assertKeys( serialized, [ 'tags_used', 'is_admin' ] )

    def test_serializers( self ):
        user = self.user_mgr.create( self.trans, **user2_data )
        all_keys = list( self.user_serializer.serializable_keyset )
        serialized = self.user_serializer.serialize( self.trans, user, all_keys )
        # pprint.pprint( serialized )

        self.log( 'everything serialized should be of the proper type' )
        self.assertEncodedId( serialized[ 'id' ] )
        self.assertDate( serialized[ 'create_time' ] )
        self.assertDate( serialized[ 'update_time' ] )
        self.assertIsInstance( serialized[ 'deleted' ], bool )
        self.assertIsInstance( serialized[ 'purged' ], bool )

        # self.assertIsInstance( serialized[ 'active' ], bool )
        self.assertIsInstance( serialized[ 'is_admin' ], bool )
        self.assertIsInstance( serialized[ 'total_disk_usage' ], float )
        self.assertIsInstance( serialized[ 'nice_total_disk_usage' ], basestring )
        self.assertIsInstance( serialized[ 'quota_percent' ], ( type( None ), float ) )
        self.assertIsInstance( serialized[ 'tags_used' ], list )
        self.assertIsInstance( serialized[ 'requests' ], list )

        self.log( 'serialized should jsonify well' )
        self.assertIsJsonifyable( serialized )


class CurrentUserSerializerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( CurrentUserSerializerTestCase, self ).set_up_managers()
        self.history_manager = histories.HistoryManager( self.app )
        self.user_serializer = users.CurrentUserSerializer( self.app )

    def test_anonymous( self ):
        anonym = None
        # need a history here for total_disk_usage
        self.trans.set_history( self.history_manager.create( self.trans ) )

        self.log( 'should be able to serialize anonymous user' )
        serialized = self.user_serializer.serialize_to_view( self.trans, anonym, view='detailed' )
        self.assertKeys( serialized,
            [ 'id', 'total_disk_usage', 'nice_total_disk_usage', 'quota_percent' ] )

        self.log( 'anonymous\'s id should be None' )
        self.assertEqual( serialized[ 'id' ], None )
        self.log( 'everything serialized should be of the proper type' )
        self.assertIsInstance( serialized[ 'total_disk_usage' ], float )
        self.assertIsInstance( serialized[ 'nice_total_disk_usage' ], basestring )
        self.assertIsInstance( serialized[ 'quota_percent' ], ( type( None ), float ) )

        self.log( 'serialized should jsonify well' )
        self.assertIsJsonifyable( serialized )


# =============================================================================
class AdminUserFilterParserTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( AdminUserFilterParserTestCase, self ).set_up_managers()
        self.filter_parser = users.AdminUserFilterParser( self.app )

    def test_parsable( self ):
        self.log( 'the following filters should be parsable' )
        self.assertORMFilter( self.filter_parser.parse_filter( 'email', 'eq', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'email', 'contains', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'email', 'like', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'username', 'eq', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'username', 'contains', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'username', 'like', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'active', 'eq', True ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'disk_usage', 'le', 500000.00 ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'disk_usage', 'ge', 500000.00 ) )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
