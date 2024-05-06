begin;
delete from knowledge where entity like 'https://apinatomy.org/uris/models/%' or entity like 'ilxtr:%';
delete from labels where entity like 'https://apinatomy.org/uris/models/%' or entity like 'ilxtr:%';
delete from publications where entity like 'https://apinatomy.org/uris/models/%' or entity like 'ilxtr:%';
delete from connectivity_models;
commit;
