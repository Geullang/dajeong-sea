import sys,unittest,hashlib, tempfile
from zipfile import ZipFile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import services as svc
from artwork import file_for,render

class DataTests(unittest.TestCase):
 def test_seven_named_areas_and_154_memberships(self):
  self.assertEqual(len(svc.AREAS),7)
  for area in svc.AREAS:
   self.assertGreaterEqual(sum(x['area']==area['id'] for x in svc.SEEDS),20)
  self.assertGreaterEqual(len(svc.SEEDS),140)
 def test_six_categories(self):
  self.assertEqual(svc.CATEGORIES,['식사','카페·디저트','독립서점','소품샵','문화·공간','자연·풍경'])
  self.assertTrue(all(x['category'] in svc.CATEGORIES for x in svc.SEEDS))
 def test_all_images_real_and_distinct(self):
  bundle=next(p for p in (ROOT/'illustrations.zip', ROOT/'assets'/'illustrations.zip') if p.is_file())
  self.assertTrue(bundle.is_file())
  expected={file_for(s['name']) for s in svc.SEEDS}
  with ZipFile(bundle) as z:
   self.assertEqual(set(z.namelist()),expected)
   hashes=[]
   for name in expected:
    image=z.read(name)
    self.assertGreater(len(image),3500)
    hashes.append(hashlib.sha256(image).hexdigest())
   self.assertEqual(len(set(hashes)),len(expected))
  self.assertTrue(any(p.is_file() for p in (ROOT/'hero.png',ROOT/'assets'/'hero.png')))
 def test_all_seed_names_unique_within_area(self):
  for a in svc.AREAS:
   names=[r['name'] for r in svc.SEEDS if r['area']==a['id']]
   self.assertEqual(len(names),len(set(names)))

class RoutingTests(unittest.TestCase):
 def setUp(self):
  self.origin={'name':'출발점','lat':35.151,'lon':129.113}
  self.places=[{'name':'A','lat':35.15,'lon':129.114,'minutes':45,'category':'문화·공간','notice':'확인 필요','address':'부산 A'},
               {'name':'B','lat':35.148,'lon':129.12,'minutes':55,'category':'식사','notice':'확인 필요','address':'부산 B'}]
 def test_measured_minutes_schedule(self):
  def route(a,b,m):return {'minutes':7,'km':.4,'shape':[a,b],'verified':True,'provider':'fixture road graph'}
  plan=svc.plan_schedule(self.origin,self.places,'10:00','13:00','도보',10,route)
  self.assertTrue(plan['fits']);self.assertTrue(plan['all_verified'])
  self.assertEqual(plan['minutes'],7+45+7+55+10)
  self.assertEqual(len(plan['ordered']),2)
 def test_deadline_and_taxi_buffer(self):
  def route(a,b,m):return {'minutes':10,'km':1,'shape':[a,b],'verified':False,'provider':'추정'}
  plan=svc.plan_schedule(self.origin,self.places,'10:00','11:00','택시',0,route)
  self.assertFalse(plan['fits']);self.assertGreater(plan['over_minutes'],0)
  self.assertEqual(plan['schedule'][0]['travel'],15)
  self.assertFalse(plan['all_verified'])
 def test_invalid_hours(self):
  with self.assertRaises(ValueError):svc.plan_schedule(self.origin,self.places,'15:00','13:00')
 def test_spherical_distance(self):
  self.assertAlmostEqual(svc.distance((35.15,129.12),(35.15,129.12)),0)
  self.assertTrue(1.0<svc.distance((35.15,129.12),(35.16,129.13))<2.0)
 def test_decode_polyline(self):
  # Standard precision-5 example multiplied is not used; precision-6 encode zero delta.
  self.assertEqual(svc.decode_polyline('????'),[(0,0),(0,0)])
 def test_route_fallback_marked_unverified(self):
  with patch('services.requests.get',side_effect=svc.requests.exceptions.Timeout()):
   data=svc.valhalla_route((35.15,129.12),(35.153,129.125),'도보')
  self.assertFalse(data['verified'])
  self.assertIn('추정',data['provider'])
  self.assertEqual(len(data['shape']),2)

class KakaoTests(unittest.TestCase):
 def test_exact_match_rejects_irrelevant(self):
  self.assertTrue(svc.match_exact('인디고서원',{'place_name':'인디고 서원'}))
  self.assertFalse(svc.match_exact('인디고서원',{'place_name':'부산역'}))
 def test_resolve_only_real_kakao_matches(self):
  area=svc.AREAS[0];lat,lon=area['center']
  def fake_api(key,query,center=None,radius=None,page=1):
   if query=='카페':return [{'place_name':'광안리해수욕장'}]
   for s in svc.SEEDS:
    if s['area']=='namcheon' and s['name']==query:
     return [{'id':str(abs(hash(query))), 'place_name':query,'y':lat,'x':lon,
        'address_name':'부산광역시 수영구','category_name':'서점'}]
   return []
  with patch('services.kakao_search',side_effect=fake_api):
   data=svc.candidates_for_area('namcheon','FAKE_KEY',max_count=25)
  self.assertGreaterEqual(len(data),20)
  self.assertTrue(all(d['address']=='부산광역시 수영구' for d in data))
  self.assertTrue(all(d['editorial'] for d in data))



class ExportTests(unittest.TestCase):
 def test_share_roundtrip_without_gps(self):
  from exports import pack_share,unpack_share
  args={'start':'10:30','end':'15:30','mode':'도보','interests':['독립서점','카페·디저트']}
  token=pack_share('namcheon',['인디고서원','무슈뱅상'],args)
  result=unpack_share(token)
  self.assertEqual(result['s'],['인디고서원','무슈뱅상'])
  self.assertEqual(result['start'],'10:30')
  self.assertNotIn('lat',str(result));self.assertNotIn('lon',str(result))
 def test_bad_share_token(self):
  from exports import unpack_share
  self.assertIsNone(unpack_share('!invalid'))
 def test_calendar_valid_components(self):
  from exports import ics_text
  schedule={'schedule':[{'arrive':'10:05','leave':'10:40'}]}
  places=[{'name':'인디고서원','address':'부산 수영구','description':'서점','notice':'운영시간 확인'}]
  text=ics_text(schedule,places)
  self.assertIn('BEGIN:VEVENT',text)
  self.assertIn('DTSTART;TZID=Asia/Seoul:20270109T100500',text)
  self.assertIn('SUMMARY:인디고서원',text)

class MultiRouteTests(unittest.TestCase):
 def test_full_trip_batch_service_one_call(self):
  from services import plan_schedule
  origin={'name':'출발','lat':35.15,'lon':129.12}
  places=[{'name':'서점','category':'독립서점','lat':35.151,'lon':129.121,'minutes':30,'notice':'','address':''},
          {'name':'카페','category':'카페·디저트','lat':35.152,'lon':129.122,'minutes':40,'notice':'','address':''}]
  calls=[]
  def backend(coords,mode):
   calls.append((coords,mode))
   return [{'minutes':8,'km':.4,'shape':[coords[i],coords[i+1]],'verified':True,'provider':'test road'} for i in range(len(coords)-1)]
  plan=plan_schedule(origin,places,'10:00','12:00',batch_route_fn=backend)
  self.assertEqual(len(calls),1)
  self.assertEqual(plan['minutes'],30+40+8+8)
  self.assertTrue(plan['all_verified'])
 def test_fallback_only_when_both_servers_fail(self):
  from services import batch_routes
  with patch('services._valhalla_batch',side_effect=svc.requests.exceptions.Timeout()),patch('services._osrm_batch',side_effect=svc.requests.exceptions.Timeout()):
   paths=batch_routes([(35.1,129.0),(35.11,129.01),(35.12,129.015)],'도보')
  self.assertEqual(len(paths),2)
  self.assertTrue(all(not p['verified'] for p in paths))
 def test_osrm_geometry_provided(self):
  response={'routes':[{'legs':[{'duration':450,'distance':500,'steps':[
   {'geometry':{'coordinates':[[129.12,35.15],[129.121,35.151]]}}]}]}]}
  class Fake:
   def raise_for_status(self):pass
   def json(self):return response
  with patch('services.requests.get',return_value=Fake()) as req:
   result=svc._osrm_batch([(35.15,129.12),(35.151,129.121)],'도보')
  self.assertTrue(result[0]['verified'])
  self.assertEqual(result[0]['shape'][0],(35.15,129.12))
  self.assertIn('routed-foot',req.call_args.args[0])

class DeploymentFallbackTests(unittest.TestCase):
 def test_data_files_embedded_in_services(self):
  import base64,zlib,io,csv,json
  restored_areas=json.loads(zlib.decompress(base64.b64decode(svc._EMBEDDED_AREAS)).decode('utf-8-sig'))
  restored_seeds=list(csv.DictReader(io.StringIO(zlib.decompress(base64.b64decode(svc._EMBEDDED_PLACES)).decode('utf-8-sig'))))
  self.assertEqual(restored_areas,svc.AREAS)
  self.assertEqual(restored_seeds,svc.SEEDS)
 def test_all_required_root_upload_files(self):
  required=['app.py','services.py','requirements.txt','artwork.py','exports.py','hero.png','illustrations.zip']
  self.assertTrue(all((ROOT/f).is_file() for f in required))

if __name__=='__main__':unittest.main(verbosity=2)
