#!/usr/bin/env python3
"""Host regressions using production methods; GPU/asset services are stubbed.

Requires Python 3 and g++. Does not run the game or establish Android stability.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def method(path, signature):
    text = (ROOT / path).read_text()
    start = text.index(signature)
    return text[start:text.index('\n  }', start) + len('\n  }')]

def run(cmd, **kwargs):
    subprocess.run(cmd, check=True, timeout=60, **kwargs)

with tempfile.TemporaryDirectory(prefix='opengothic-a25-') as tmp:
    out = Path(tmp)
    source = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <set>
#include <string>
#include <string_view>
#include <vector>
#include "utils/string_frm.h"
struct Texture2d {};
struct Resources {
  static std::vector<std::string> names;
  static const Texture2d* loadTexture(std::string_view name) {
    static Texture2d texture;
    names.emplace_back(name);
    return name.find("_A0") != name.npos || name.find("_A1") != name.npos ? &texture : nullptr;
  }
  static std::vector<const Texture2d*> loadTextureAnim(std::string_view name);
};
std::vector<std::string> Resources::names;
namespace zenkit { enum class AnimationType { NONE, WIND, WIND_ALT }; }
struct DrawCommands {
  enum Type { Landscape, Static, Morph };
  void addClusters(unsigned, unsigned) {}
};
struct PackedMesh { static constexpr unsigned MaxInd = 3; };
struct VisualObjects {
  struct Object {
    unsigned iboLen = 3, cmdId = 0, clusterId = 0;
    DrawCommands::Type type = DrawCommands::Static;
    zenkit::AnimationType wind = zenkit::AnimationType::NONE;
    bool live = false;
    bool isEmpty() const { return !live; }
  };
  struct Clusters { void free(unsigned, unsigned) {} } clustersMem;
  DrawCommands drawCmd;
  std::vector<Object> objects;
  std::set<size_t> objectsFree, objectsWind, objectsMorph;
  void updateRtAs(size_t) {}
  void free(size_t id);
};
'''
    source += method('common/resources.cpp', 'std::vector<const Texture2d*> Resources::loadTextureAnim')
    source += '\n' + method('common/graphics/visualobjects.cpp', 'void VisualObjects::free(size_t id)')
    source += r'''
int main() {
  assert(Resources::loadTextureAnim("plain.tga").empty());
  for(size_t length: {0u, 120u, 124u, 125u, 126u, 127u, 128u, 129u, 256u, 4096u}) {
    Resources::names.clear();
    std::string prefix(length, 'x');
    auto frames = Resources::loadTextureAnim(prefix + "_a0.tga");
    assert(frames.size() == 2);
    assert(Resources::names[0] == std::string(length, 'X') + "_A0.TGA");
    assert(Resources::names[1] == std::string(length, 'X') + "_A1.TGA");
  }
  for(auto wind: {zenkit::AnimationType::NONE, zenkit::AnimationType::WIND, zenkit::AnimationType::WIND_ALT}) {
    for(unsigned repeat=0; repeat<1000; ++repeat) {
      VisualObjects v;
      v.objects.resize(3);
      for(auto& obj:v.objects) { obj.live=true; obj.wind=wind; }
      if(wind!=zenkit::AnimationType::NONE) v.objectsWind={0,1,2};
      v.free(1); // interior id: must not animate a reused object
      assert(v.objectsWind.count(1)==0);
      v.objects[1].live=true;
      v.free(2); // trailing id: vector shrinks
      for(auto id:v.objectsWind) assert(id<v.objects.size() && v.objects.at(id).live);
      v.free(1);
      v.free(0);
      assert(v.objects.empty() && v.objectsWind.empty());
    }
  }
}
'''
    (out/'regressions.cpp').write_text(source)
    flags = ['g++', '-std=c++20', '-O1', '-g', '-fno-omit-frame-pointer',
             '-fsanitize=address,undefined', '-fno-pie', '-no-pie', '-pthread', '-I', str(ROOT/'common')]
    run(flags + [str(out/'regressions.cpp'), '-o', str(out/'regressions')])
    run([str(out/'regressions')])
    print('PASS: production texture-name and object-free methods (ASan/UBSan)', flush=True)

    # Only unused Tempest includes are replaced. Compile the production pool
    # and real string_frm; emulate CPU counts to exercise shutdown on small pools.
    workers = (ROOT/'common/utils/workers.cpp').read_text()
    workers = workers.replace('#include <Tempest/Platform>', 'namespace Tempest {}')
    workers = workers.replace('#include <Tempest/Log>', '')
    (out/'workers_test.cpp').write_text(r'''
#include "utils/workers.h"
#include <cassert>
int main() {
  std::vector<unsigned> data(4097);
  for(unsigned round=0; round<100; ++round) {
    Workers::parallelFor(data, [](unsigned& value) { ++value; });
    std::vector<std::atomic<unsigned>> seen(257);
    Workers::parallelTasks(seen.size(), [&](size_t id) { assert(id<seen.size()); ++seen[id]; });
    for(auto& count:seen) assert(count==1);
    Workers::parallelTasks(size_t(0), [](size_t) { assert(false); });
    Workers::parallelTasks(size_t(1), [](size_t id) { assert(id==0); });
  }
  for(auto value:data) assert(value==100);
  for(size_t size: {0u,1u,16u,128u,129u,256u,257u}) {
    std::vector<unsigned> small(size);
    Workers::parallelFor(small, [](unsigned& value) { ++value; });
    for(auto value:small) assert(value==1);
  }
}
''')
    for cpus in [0, 1, 2, 8, 16]:
        (out/'workers.cpp').write_text(workers.replace('std::thread::hardware_concurrency()', str(cpus)))
        run(flags + ['-I', str(ROOT/'common/utils'), str(out/'workers.cpp'),
                     str(out/'workers_test.cpp'), '-o', str(out/'workers_test')])
        run([str(out/'workers_test')])
        print(f'PASS: pool completion, exact-once tasks and shutdown; CPUs={cpus} (ASan/UBSan)', flush=True)
