import datetime, os
from peewee import *

class DatabaseConfig:
    """
    Configures the database, a static class
    that does not need to be instantiated

    get: Get the database
    set(path): Set the SQLite database by path
    """
    __database = DatabaseProxy()
    
    @staticmethod
    def get():
        """
        Gets the database
        """
        return DatabaseConfig.__database

    @staticmethod
    def is_set():
        """
        Checks if the database is set,
        that is, if it is not None or a DatabaseProxy
        """
        return type(DatabaseConfig.__database).__name__ not in ['NoneType', 'DatabaseProxy']
    
    @staticmethod
    def set(path: str):
        """
        Sets the database by path
        """
        database = SqliteDatabase(path)
        DatabaseConfig.__database.initialize(database)
        DatabaseConfig.__database.create_tables([Project,
             Release,
             ReleaseDependency,
             ReleaseRepo,
             CPE])
        DatabaseConfig.__database.close()



class CPE(Model):
    """
    CPE models a Common Platform Enumeration

    id: The CPE id
    vendor: The vendor of the CPE
    platform: The platform of the CPE (e.g. pypi)
    product: The product of the CPE
    version: The version of the CPE
    language: The language of the CPE
    updated_at: The date the row in the database was updated
    """
    id = AutoField()
    platform = CharField(null=True)
    vendor = CharField(null=False)
    product = CharField(null=False)
    version = CharField(null=True)
    version_start_including = CharField(null=True)
    version_end_excluding = CharField(null=True)
    language = CharField(null=True)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = DatabaseConfig.get()
        table_name = 'cpes'

class Project(Model):
    """
    Project models a libraries.io project,
    that is, a Python package etc

    id: The project id
    name: The project name
    platform: The platform the project is on
    language: The language the project is written in
    updated_at: The date the row in the database was updated
    """
    id = AutoField()
    name = CharField(null=False)
    platform = CharField(null=False)
    language = CharField(null=True)
    contributions = IntegerField(null=True)
    homepage = CharField(null=True)
    vendor_name = CharField(null=True)
    stars = IntegerField(null=True)
    forks = IntegerField(null=True)
    dependent_repos = IntegerField(null=True)
    dependent_projects = IntegerField(null=True)
    updated_at = DateTimeField(default=datetime.datetime.now)
    package_manager_url = CharField(null=True)
    repository_url = CharField(null=True)

    class Meta:
        database = DatabaseConfig.get()
        table_name = 'projects'

class Release(Model):
    """
    Release models a release of a project
    
    id: The release id
    project_id: The project id
    published_at: The date the release was published
    version_number: The version number of the release
    updated_at: The date the row in the database was updated
    """
    id = AutoField()
    project_id = ForeignKeyField(Project, backref='releases')
    published_at = DateTimeField(null=True)
    version_number = CharField(null=False)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = DatabaseConfig.get()
        table_name = 'releases'

class ReleaseDependency(Model):
    """
    ReleaseDependency models a release's dependencies

    release_id: The release id
    name: The name of the dependency
    project_name: The name of the project the dependency is on, usually the same as the name
    platform: The platform the dependency is on
    requirements: The version requirements of the dependency
    updated_at: The date the row in the database was updated
    """
    
    release_id = ForeignKeyField(Release, backref='dependencies')
    name = CharField(null=False)
    project_name = CharField(null=False)
    platform = CharField(null=True)
    requirements = CharField(null=True)
    updated_at = DateTimeField(default=datetime.datetime.now)
    optional = BooleanField(default=False)

    class Meta:
        database = DatabaseConfig.get()
        table_name = 'release_dependencies'

class ReleaseRepo(Model):
    """
    ReleaseRepo models a release's repository

    release_id: The release id
    repo_url: The URL of the repository
    updated_at: The date the row in the database was updated
    """
    release_id = ForeignKeyField(Release, backref='repos')
    repo_url = CharField(null=False)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = DatabaseConfig.get()
        table_name = 'release_repos'