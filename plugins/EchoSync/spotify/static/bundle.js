//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function y(e) {
	return e();
}
function b(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function x() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var S = 1024, C = 2048, w = 4096, ee = 8192, te = 16384, ne = 32768, re = 1 << 25, ie = 65536, ae = 1 << 19, oe = 1 << 20, se = 1 << 25, ce = 65536, le = 1 << 21, ue = 1 << 22, de = 1 << 23, fe = Symbol("$state"), pe = Symbol("legacy props"), me = Symbol(""), he = Symbol("attributes"), ge = Symbol("class"), _e = Symbol("style"), ve = Symbol("text"), ye = Symbol("form reset"), be = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), xe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Se(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Ce() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function we(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function Te(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ee() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function De(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Oe() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function ke() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ae(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function je() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ne() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Pe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Fe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ie(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Le() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function Re(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw Ie(), r;
	return E = e;
}
function ze() {
	return D(/* @__PURE__ */ cn(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ cn(E) !== null) throw Ie(), r;
		E = e;
	}
}
function Be(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ cn(n);
		E = n;
	}
}
function Ve(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ cn(n);
		e && n.remove(), n = i;
	}
}
function He(e) {
	if (!e || e.nodeType !== 8) throw Ie(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ue(e) {
	return e === this.v;
}
function We(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ge(e) {
	return !We(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var k = null;
function Ke(e) {
	k = e;
}
function qe(e, n = !1, r) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Je(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) Cn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, e ?? {};
}
function Ye() {
	return !t || k !== null && k.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], b(e);
}
function Qe(e) {
	if (Xe.length === 0 && !pt) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function $e() {
	for (; Xe.length > 0;) Ze();
}
function et(e) {
	var t = G;
	if (t === null) return H.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	tt(e, t);
}
function tt(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var nt = ~(C | w | S);
function A(e, t) {
	e.f = e.f & nt | t;
}
function rt(e) {
	e.f & 512 || e.deps === null ? A(e, S) : A(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function it(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ce, it(t.deps));
}
function at(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), it(e.deps), A(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var ot = !1, st = !1;
function ct(e) {
	var t = st;
	try {
		return st = !1, [e(), st];
	} finally {
		st = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var lt = null, ut = null, j = null, dt = null, M = null, ft = null, pt = !1, mt = !1, ht = null, gt = null, _t = 0, vt = 1, yt = class t {
	id = vt++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	unblocked = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = /* @__PURE__ */ new Set();
	#o = 0;
	#s = /* @__PURE__ */ new Map();
	#c = null;
	#l = [];
	#u = [];
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Map();
	#m = /* @__PURE__ */ new Set();
	is_fork = !1;
	#h = !1;
	#g() {
		if (this.is_fork) return !0;
		for (let n of this.#s.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#p.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#p.has(e) || this.#p.set(e, {
			d: [],
			m: []
		}), this.#m.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#p.get(e);
		if (n) {
			this.#p.delete(e);
			for (var r of n.d) A(r, C), t(r);
			for (r of n.m) A(r, w), t(r);
		}
		this.#m.add(e);
	}
	#_() {
		if (this.#e = !0, _t++ > 1e3 && (this.#w(), xt()), !this.#g()) {
			for (let e of this.#d) this.#f.delete(e), A(e, C), this.schedule(e);
			for (let e of this.#f) A(e, w), this.schedule(e);
		}
		let n = this.#l;
		this.#l = [], this.apply();
		var r = ht = [], i = [], a = gt = [];
		for (let e of n) try {
			this.#v(e, r, i);
		} catch (t) {
			throw Dt(e), t;
		}
		if (j = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (ht = null, gt = null, this.#g()) {
			this.#x(i), this.#x(r);
			for (let [e, t] of this.#p) Et(e, t);
			a.length > 0 && j.#_();
			return;
		}
		let s = this.#y();
		if (s) {
			s.#b(this);
			return;
		}
		this.#d.clear(), this.#f.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), dt = this, St(i), St(r), dt = null, this.#c?.resolve();
		var c = j;
		if (this.linked && this.#o === 0 && this.#w(), e && !this.linked && (this.#S(), j = c), this.#l.length > 0) {
			c === null && (c = this, this.#C());
			let e = c;
			e.#l.push(...this.#l.filter((t) => !e.#l.includes(t)));
		}
		c !== null && c.#_();
	}
	#v(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#p.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : er(i) && (a & 16 && this.#f.add(i), ar(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#y() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#b(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve);
		}
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#f.delete(i), A(i, C), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#w(), j = this, this.#_();
	}
	#x(e) {
		for (var t = 0; t < e.length; t += 1) at(e[t], this.#d, this.#f);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			mt = !0, j = this, this.#_();
		} finally {
			_t = 0, ft = null, ht = null, gt = null, mt = !1, j = null, M = null, Kt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear(), this.#a.clear(), this.#w();
	}
	register_created_effect(e) {
		this.#u.push(e);
	}
	#S() {
		this.#w();
		for (let l = lt; l !== null; l = l.#n) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			if (e) for (let [e, t] of this.async_deriveds) {
				let n = l.async_deriveds.get(e);
				n && t.promise.then(n.resolve);
			}
			if (l.#e) {
				var r = [...l.current.keys()].filter((e) => !this.current.has(e));
				if (r.length === 0) e && l.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#m) l.unskip_effect(e, (e) => {
						e.f & 4194320 ? l.schedule(e) : l.#x([e]);
					});
					l.activate();
					var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
					for (var o of t) Ct(o, r, i, a);
					a = /* @__PURE__ */ new Map();
					var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e.v : !0);
					if (s.length > 0) for (let e of this.#u) !(e.f & 155648) && wt(e, s, a) && (e.f & 4194320 ? (A(e, C), l.schedule(e)) : l.#d.add(e));
					if (l.#l.length > 0) {
						l.apply();
						for (var c of l.#l) l.#v(c, [], []);
						l.#l = [];
					}
					l.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#o += 1, e) {
			let e = this.#s.get(t) ?? 0;
			this.#s.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#o, e) {
			let e = this.#s.get(t) ?? 0;
			e === 1 ? this.#s.delete(t) : this.#s.set(t, e - 1);
		}
		this.#h || (this.#h = !0, Qe(() => {
			this.#h = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#d.add(t);
		for (let e of t) this.#f.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	on_fork_commit(e) {
		this.#a.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#a) e(this);
		this.#a.clear();
	}
	settled() {
		return (this.#c ??= x()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new t();
			e.#C(), !mt && !pt && Qe(() => {
				e.#e || e.flush();
			});
		}
		return j;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			M = null;
			return;
		}
		M = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) M.set(e, t);
		for (let e = lt; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) M.has(t) || M.set(t, n);
		}
	}
	schedule(t) {
		if (ft = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (ht !== null && n === G && (e || (H === null || !(H.f & 2)) && !ot)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#l.push(n);
	}
	#C() {
		ut === null ? lt = ut = this : (ut.#n = this, this.#t = ut), ut = this;
	}
	#w() {
		var e = this.#t, t = this.#n;
		e === null ? lt = t : e.#n = t, t === null ? ut = e : t.#t = e, this.linked = !1;
	}
};
function bt(e) {
	var t = pt;
	pt = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if ($e(), j === null) return n;
			j.flush();
		}
	} finally {
		pt = t;
	}
}
function xt() {
	try {
		Oe();
	} catch (e) {
		tt(e, ft);
	}
}
var N = null;
function St(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && er(r) && (N = /* @__PURE__ */ new Set(), ar(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && In(r), N?.size > 0)) {
				Kt.clear();
				for (let e of N) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) N.has(n) && (N.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || ar(n);
					}
				}
				N.clear();
			}
		}
		N = null;
	}
}
function Ct(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? Ct(i, t, n, r) : e & 4194320 && !(e & 2048) && wt(i, t, r) && (A(i, C), Tt(i));
	}
}
function wt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && wt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Tt(e) {
	j.schedule(e);
}
function Et(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), A(e, S);
		for (var n = e.first; n !== null;) Et(n, t), n = n.next;
	}
}
function Dt(e) {
	A(e, S);
	for (var t = e.first; t !== null;) Dt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function Ot(e) {
	let t = 0, n = Jt(0), r;
	return () => {
		bn() && (X(n), kn(() => (t === 0 && (r = Z(() => e(() => Qt(n)))), t += 1, () => {
			Qe(() => {
				--t, t === 0 && (r?.(), r = void 0, Qt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var kt = ie | ae;
function At(e, t, n, r) {
	new jt(e, t, n, r);
}
var jt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = Ot(() => (this.#m = Jt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = jn(() => {
			if (T) {
				let e = this.#t;
				ze();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, kt), T && (this.#e = E);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = B(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), Qe(() => {
			var e = this.#c = document.createDocumentFragment(), t = I();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Ln(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Vn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(j);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		at(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = H, r = k;
		Kn(this.#i), W(this.#i), Ke(this.#i.ctx);
		try {
			return yt.ensure(), e();
		} catch (e) {
			return et(e), null;
		} finally {
			Kn(t), W(n), Ke(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Ln(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Qe(() => {
			this.#d = !1, this.#m && Xt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), X(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), T && (D(this.#t), Be(), D(Ve()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Le();
				return;
			}
			r = !0, i && Pe(), this.#s !== null && Ln(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				tt(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return tt(e, this.#i.parent), null;
				}
			}));
		};
		Qe(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				tt(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => tt(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Mt(e, t, n, r) {
	let i = Ye() ? It : zt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = G, s = Nt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		if (!(o.f & 16384)) {
			s();
			try {
				r(e);
			} catch (e) {
				tt(e, o);
			}
			Pt();
		}
	}
	var u = Ft();
	if (n.length === 0) {
		c.then(() => l(t.map(i))).finally(u);
		return;
	}
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ Rt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => tt(e, o)).finally(u);
	}
	c ? c.then(() => {
		s(), d(), Pt();
	}) : d();
}
function Nt() {
	var e = G, t = H, n = k, r = j;
	return function(i = !0) {
		Kn(e), W(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Pt(e = !0) {
	Kn(null), W(null), Ke(null), e && j?.deactivate();
}
function Ft() {
	var e = G, t = e.b, n = j, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), () => {
		t.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function It(e) {
	var t = 2 | C;
	return G !== null && (G.f |= ae), {
		ctx: k,
		deps: null,
		effects: null,
		equals: Ue,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
var Lt = Symbol("obsolete");
/* @__NO_SIDE_EFFECTS__ */
function Rt(e, t, n) {
	let r = G;
	r === null && Ce();
	var a = void 0, o = Jt(i), s = !H, c = /* @__PURE__ */ new Set();
	return On(() => {
		var t = G, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== be && n.reject(e);
			}).finally(Pt);
		} catch (e) {
			n.reject(e), Pt();
		}
		var i = j;
		if (s) {
			if (t.f & 32768) var l = Ft();
			if (r.b.is_rendered()) i.async_deriveds.get(t)?.reject(Lt);
			else for (let e of c.values()) e.reject(Lt);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== Lt && (i.activate(), t ? (o.f |= de, Xt(o, t)) : (o.f & 8388608 && (o.f ^= de), Xt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), xn(() => {
		for (let e of c) e.reject(Lt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function zt(e) {
	let t = /* @__PURE__ */ It(e);
	return t.equals = Ge, t;
}
function Bt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Vt(e) {
	var t, n = G, r = e.parent;
	if (!Wn && r !== null && r.f & 24576) return Fe(), e.v;
	Kn(r);
	try {
		e.f &= ~ce, Bt(e), t = nr(e);
	} finally {
		Kn(n);
	}
	return t;
}
function Ht(e) {
	var t = Vt(e);
	if (!e.equals(t) && (e.wv = $n(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : (j.capture(e, t, !0), dt?.capture(e, t, !0)), e.deps === null))) {
		A(e, S);
		return;
	}
	Wn || (M === null ? rt(e) : (bn() || j?.is_fork) && M.set(e, t));
}
function Ut(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(be), t.teardown = v, t.ac = null, ir(t, 0), Nn(t));
}
function Wt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && ar(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Gt = /* @__PURE__ */ new Set(), Kt = /* @__PURE__ */ new Map(), qt = !1;
function Jt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ue,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Yt(e, t) {
	let n = Jt(e, t);
	return qn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = Jt(e);
	return n || (i.equals = Ge), t && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Ye() && H.f & 4325394 && (K === null || !c.call(K, e)) && Ne(), Xt(e, n ? en(t) : t, gt);
}
function Xt(e, t, n = null) {
	if (!e.equals(t)) {
		Kt.set(e, Wn ? t : e.v);
		var r = yt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Vt(t), M === null && rt(t);
		}
		e.wv = $n(), $t(e, C, n), Ye() && G !== null && G.f & 1024 && !(G.f & 96) && (Y === null ? Jn([e]) : Y.push(e)), !r.is_fork && Gt.size > 0 && !qt && Zt();
	}
	return t;
}
function Zt() {
	qt = !1;
	for (let e of Gt) {
		e.f & 1024 && A(e, w);
		let t;
		try {
			t = er(e);
		} catch {
			t = !0;
		}
		t && ar(e);
	}
	Gt.clear();
}
function Qt(e) {
	F(e, e.v + 1);
}
function $t(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & C) === 0;
			if (l && A(s, t), c & 131072) Gt.add(s);
			else if (c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= ce), $t(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && N !== null && N.add(d), n === null ? Tt(d) : n.push(d);
			}
		}
	}
}
function en(e) {
	if (typeof e != "object" || !e || fe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Yt(0), s = null, c = Zn, l = (e) => {
		if (Zn === c) return e();
		var t = H, n = Zn;
		W(null), Qn(c);
		var r = e();
		return W(t), Qn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Yt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && je();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Yt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Yt(i, s));
					n.set(t, e), Qt(a);
				}
			} else F(r, i), Qt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === fe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Yt(en(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = X(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = X(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === fe) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Yt(a ? en(e[t]) : i, s)), n.set(t, r)), X(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Yt(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Yt(void 0, s)), F(u, en(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => en(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Qt(a);
			}
			return !0;
		},
		ownKeys(e) {
			X(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Me();
		}
	});
}
var tn, nn, rn, an;
function on() {
	if (tn === void 0) {
		tn = window, nn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		rn = f(t, "firstChild").get, an = f(t, "nextSibling").get, _(e) && (e[ge] = void 0, e[he] = null, e[_e] = void 0, e.__e = void 0), _(n) && (n[ve] = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function sn(e) {
	return rn.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function cn(e) {
	return an.call(e);
}
function L(e, t) {
	if (!T) return /* @__PURE__ */ sn(e);
	var n = /* @__PURE__ */ sn(E);
	if (n === null) n = E.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), D(r), r;
	}
	return t && pn(n), D(n), n;
}
function ln(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ sn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ cn(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = I();
			return E?.before(r), D(r), r;
		}
		pn(E);
	}
	return E;
}
function R(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ cn(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		pn(r);
	}
	return D(r), r;
}
function un(e) {
	e.textContent = "";
}
function dn() {
	return !e || N !== null ? !1 : (G.f & ne) !== 0;
}
function fn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function pn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var mn = !1;
function hn() {
	mn || (mn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ye]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function gn(e) {
	var t = H, n = G;
	W(null), Kn(null);
	try {
		return e();
	} finally {
		W(t), Kn(n);
	}
}
function _n(e, t, n, r = n) {
	e.addEventListener(t, () => gn(n));
	let i = e[ye];
	i ? e[ye] = () => {
		i(), r(!0);
	} : e[ye] = () => r(!0), hn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function vn(e) {
	G === null && (H === null && De(e), Ee()), Wn && Te(e);
}
function yn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: k,
		deps: null,
		nodes: null,
		f: e | C | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) ht === null ? yt.ensure().schedule(r) : ht.push(r);
	else if (t !== null) {
		try {
			ar(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && yn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function bn() {
	return H !== null && !U;
}
function xn(e) {
	let t = z(8, null);
	return A(t, S), t.teardown = e, t;
}
function Sn(e) {
	vn("$effect");
	var t = G.f;
	if (!H && t & 32 && !(t & 32768)) {
		var n = k;
		(n.e ??= []).push(e);
	} else return Cn(e);
}
function Cn(e) {
	return z(4 | oe, e);
}
function wn(e) {
	return vn("$effect.pre"), z(8 | oe, e);
}
function Tn(e) {
	yt.ensure();
	let t = z(64 | ae, e);
	return () => {
		V(t);
	};
}
function En(e) {
	yt.ensure();
	let t = z(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Ln(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function Dn(e) {
	return z(4, e);
}
function On(e) {
	return z(ue | ae, e);
}
function kn(e, t = 0) {
	return z(8 | t, e);
}
function An(e, t = [], n = [], r = []) {
	Mt(r, t, n, (t) => {
		z(8, () => e(...t.map(X)));
	});
}
function jn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | ae, e);
}
function Mn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Wn, n = H;
		Gn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Gn(e), W(n);
		}
	}
}
function Nn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && gn(() => {
			e.abort(be);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Pn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Fn(e.nodes.start, e.nodes.end), n = !0), A(e, re), Nn(e, t && !n), ir(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Mn(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && In(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Fn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ cn(e);
		e.remove(), e = n;
	}
}
function In(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Ln(e, t, n = !0) {
	var r = [];
	Rn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Rn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Rn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function zn(e) {
	Bn(e, !0);
}
function Bn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (A(e, C), yt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Bn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Vn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ cn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Hn = null, Un = !1, Wn = !1;
function Gn(e) {
	Wn = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function Kn(e) {
	G = e;
}
var K = null;
function qn(t) {
	H !== null && (!e || H.f & 2) && (K === null ? K = [t] : K.push(t));
}
var q = null, J = 0, Y = null;
function Jn(e) {
	Y = e;
}
var Yn = 1, Xn = 0, Zn = Xn;
function Qn(e) {
	Zn = e;
}
function $n() {
	return ++Yn;
}
function er(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ce), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (er(a) && Ht(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, S);
	}
	return !1;
}
function tr(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && K !== null && c.call(K, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? tr(o, n, !1) : n === o && (r ? A(o, C) : o.f & 1024 && A(o, w), Tt(o));
	}
}
function nr(e) {
	var t = q, n = J, r = Y, i = H, a = K, o = k, s = U, c = Zn, l = e.f;
	q = null, J = 0, Y = null, H = l & 96 ? null : e, K = null, Ke(e.ctx), U = !1, Zn = ++Xn, e.ac !== null && (gn(() => {
		e.ac.abort(be);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = j?.is_fork;
		if (q !== null) {
			var m;
			if (p || ir(e, J), f !== null && J > 0) for (f.length = J + q.length, m = 0; m < q.length; m++) f[J + m] = q[m];
			else e.deps = f = q;
			if (bn() && e.f & 512) for (m = J; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && J < f.length && (ir(e, J), f.length = J);
		if (Ye() && Y !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < Y.length; m++) tr(Y[m], e);
		if (i !== null && i !== e) {
			if (Xn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Xn;
			if (t !== null) for (let e of t) e.rv = Xn;
			Y !== null && (r === null ? r = Y : r.push(...Y));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return et(e);
	} finally {
		e.f ^= le, q = t, J = n, Y = r, H = i, K = a, Ke(o), U = s, Zn = c;
	}
}
function rr(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (q === null || !c.call(q, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ce), o.v !== i && rt(o), Ut(o), ir(o, 0);
	}
}
function ir(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) rr(e, n[r]);
}
function ar(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, S);
		var n = G, r = Un;
		G = e, Un = !0;
		try {
			t & 16777232 ? Pn(e) : Nn(e), Mn(e);
			var i = nr(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Yn;
		} finally {
			Un = r, G = n;
		}
	}
}
async function or() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), bt();
}
function X(e) {
	var t = (e.f & 2) != 0;
	if (Hn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (K === null || !c.call(K, e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Xn && (e.rv = Xn, q === null && n !== null && n[J] === e ? J++ : q === null ? q = [e] : q.push(e));
		else {
			(H.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (Wn && Kt.has(e)) return Kt.get(e);
	if (t) {
		var i = e;
		if (Wn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || cr(i)) && (a = Vt(i)), Kt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Un || (H.f & 512) != 0), s = (i.f & ne) === 0;
		er(i) && (o && (i.f |= 512), Ht(i)), o && !s && (Wt(i), sr(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function sr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Wt(t), sr(t));
}
function cr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Kt.has(t) || t.f & 2 && cr(t)) return !0;
	return !1;
}
function Z(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function lr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) ur(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && ur(n);
		}
	}
}
function ur(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ur(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var dr = Symbol("events"), fr = /* @__PURE__ */ new Set(), pr = /* @__PURE__ */ new Set();
function mr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || _r.call(t, e), !e.cancelBubble) return gn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function hr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = mr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && xn(() => {
		t.removeEventListener(e, o, a);
	});
}
var gr = null;
function _r(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	gr = e;
	var o = 0, s = gr === e && e[dr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[dr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = H, f = G;
		W(null), Kn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[dr]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[dr] = t, delete e.currentTarget, W(u), Kn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var vr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function yr(e) {
	return vr?.createHTML(e) ?? e;
}
function br(e) {
	var t = fn("template");
	return t.innerHTML = yr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function xr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (T) return xr(E, null), E;
		i === void 0 && (i = br(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ sn(i)));
		var t = r || nn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ sn(t), s = t.lastChild;
			xr(o, s);
		} else xr(t, t);
		return t;
	};
}
function $(e, t) {
	if (T) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = E), ze();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var Sr = ["touchstart", "touchmove"];
function Cr(e) {
	return Sr.includes(e);
}
function wr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ve] ??= e.nodeValue) && (e[ve] = n, e.nodeValue = `${n}`);
}
function Tr(e, t) {
	return Or(e, t);
}
function Er(e, t) {
	on(), t.intro = t.intro ?? !1;
	let n = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ sn(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ cn(o);
		if (!o) throw r;
		Re(!0), D(o);
		let i = Or(e, {
			...t,
			anchor: o
		});
		return Re(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && ke(), on(), un(n), Re(!1), Tr(e, t);
	} finally {
		Re(i), D(a);
	}
}
var Dr = /* @__PURE__ */ new Map();
function Or(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	on();
	var u = void 0, d = En(() => {
		var s = n ?? t.appendChild(I());
		At(s, { pending: () => {} }, (t) => {
			qe({});
			var n = k;
			if (o && (n.c = o), a && (i.$$events = a), T && xr(t, null), u = e(t, i) || {}, T && (G.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw Ie(), r;
			Je();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = Cr(r);
					for (let e of [t, document]) {
						var a = Dr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Dr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, _r, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(fr)), pr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = Dr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, _r), r.delete(e), r.size === 0 && Dr.delete(n)) : r.set(e, i);
			}
			pr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return kr.set(u, d), u;
}
var kr = /* @__PURE__ */ new WeakMap();
function Ar(e, t) {
	let n = kr.get(e);
	return n ? (kr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var jr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) zn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Vn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Ln(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = dn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = I();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function Mr(e) {
	k === null && Se("onMount"), t && k.l !== null ? Nr(k).m.push(e) : Sn(() => {
		let t = Z(e);
		if (typeof t == "function") return t;
	});
}
function Nr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Pr(e, t, n = !1) {
	var r;
	T && (r = E, ze());
	var i = new jr(e), a = n ? ie : 0;
	function o(e, t) {
		if (T) {
			var n = He(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ve();
				D(a), i.anchor = a, Re(!1), i.ensure(e, t), Re(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	jn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Fr(e, t) {
	return t;
}
function Ir(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Ln(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Lr(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			un(d), d.append(u), e.items.clear();
		}
		Lr(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Lr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= se, Vn(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var Rr;
function zr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = T ? D(/* @__PURE__ */ sn(u)) : u.appendChild(I());
	}
	T && ze();
	var d = null, f = /* @__PURE__ */ zt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Vr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= se, Ur(d, null, s)) : zn(d) : Ln(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: jn(() => {
			p = X(f);
			var e = p.length;
			let o = !1;
			T && He(s) === "[!" != (e === 0) && (s = Ve(), D(s), Re(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = j, v = dn(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, o = !0, Re(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Xt(S.v, b), S.i && Xt(S.i, y), v && u.unskip_effect(S.e)) : (S = Hr(c, h ? s : Rr ??= I(), b, x, y, i, t, n), h || (S.e.f |= se), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = B(() => a(s)) : (d = B(() => a(Rr ??= I())), d.f |= se)), e > l.size && we("", "", ""), T && e > 0 && D(Ve()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Re(!0), X(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, T && (s = E);
}
function Br(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Vr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Br(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (zn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= se, _ === c) Ur(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Wr(e, d, _), Wr(e, _, y), Ur(_, y, n), d = _, p = [], m = [], c = Br(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Ur(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Wr(e, S.prev, C.next), Wr(e, d, S), Wr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Ur(_, c, n), Wr(e, _.prev, _.next), Wr(e, _, d === null ? e.effect.first : d.next), Wr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Br(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Br(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Lr(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Br(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Ir(e, w, te);
		}
	}
	a && Qe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Hr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Jt(n) : /* @__PURE__ */ P(n, !1, !1) : null, l = o & 2 ? Jt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Ur(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ cn(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Wr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Gr(e, t) {
	Dn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = fn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Kr = Symbol("is custom element"), qr = Symbol("is html"), Jr = xe ? "link" : "LINK";
function Yr(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Zr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Zr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ye] = n, Qe(n), hn();
	}
}
function Xr(e, t) {
	var n = Qr(e);
	n.checked !== (n.checked = t ?? void 0) && (e.checked = t);
}
function Zr(e, t, n, r) {
	var i = Qr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Jr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ei(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Qr(e) {
	return e[he] ??= {
		[Kr]: e.nodeName.includes("-"),
		[qr]: e.namespaceURI === a
	};
}
var $r = /* @__PURE__ */ new Map();
function ei(e) {
	var t = e.getAttribute("is") || e.nodeName, n = $r.get(t);
	if (n) return n;
	$r.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ti(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	_n(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = ni(t) ? ri(a) : a, r(a), j !== null && i.add(j), await or(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && t.defaultValue !== t.value || Z(n) == null && t.value) && (r(ni(t) ? ri(t.value) : t.value), j !== null && i.add(j)), kn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? dt : j;
			if (i.has(a)) return;
		}
		ni(t) && r === ri(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function ni(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ri(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ii(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => lr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ It(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => X(i);
	}
	n.b.length && wn(() => {
		ai(t, r), b(n.b);
	}), Sn(() => {
		let e = Z(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && Sn(() => {
		ai(t, r), b(n.a);
	});
}
function ai(e, t) {
	if (e.l.s) for (let t of e.l.s) X(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function oi(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ It(i), X(u)) : (l && (l = !1, c = s ? Z(i) : i), c);
	let p;
	if (o) {
		var m = fe in e || pe in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ct(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && Ae(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? It : zt)(() => (y = !1, _()));
	o && X(b);
	var x = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? X(b) : a && o ? en(e) : e;
			return F(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Wn && y || x.f & 16384 ? b.v : X(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function si(e) {
	return new ci(e);
}
var ci = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return X(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === pe ? !0 : (X(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Er : Tr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && bt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Ar(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, li;
typeof HTMLElement == "function" && (li = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = fn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = di(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ui(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = si({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Tn(() => {
				kn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ui(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ui(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function ui(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function di(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function fi(e, t, n, r, i, a) {
	let o = class extends li {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = ui(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region SpotifyCard.svelte
var pi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-16m7f8c\"><div class=\"spinner svelte-16m7f8c\"></div> <span>Initializing Spotify Nexus...</span></div>"), mi = /* @__PURE__ */ Q("<div class=\"form-grid svelte-16m7f8c\"><div class=\"form-field svelte-16m7f8c\"><span class=\"field-label svelte-16m7f8c\">Client ID</span> <input type=\"text\" placeholder=\"Spotify Developer Client ID\" class=\"input-field svelte-16m7f8c\"/></div> <div class=\"form-field svelte-16m7f8c\"><span class=\"field-label svelte-16m7f8c\">Client Secret</span> <div class=\"password-wrapper\"><input type=\"password\" placeholder=\"Spotify Developer Client Secret\" class=\"input-field svelte-16m7f8c\"/></div></div> <div class=\"form-field svelte-16m7f8c\"><span class=\"field-label svelte-16m7f8c\">Redirect URI</span> <input type=\"text\" class=\"input-field readonly svelte-16m7f8c\" readonly=\"\" disabled=\"\"/> <span class=\"helper-text svelte-16m7f8c\">Whitelist this in Spotify Dashboard</span></div> <div class=\"actions-row svelte-16m7f8c\"><button class=\"btn-primary svelte-16m7f8c\"> </button></div></div>"), hi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-16m7f8c\"> </button>"), gi = /* @__PURE__ */ Q("<div class=\"add-account-form svelte-16m7f8c\"><div class=\"form-field svelte-16m7f8c\"><input type=\"text\" placeholder=\"e.g. My Personal Account\" class=\"input-field svelte-16m7f8c\"/></div> <div class=\"actions-row svelte-16m7f8c\"><button class=\"btn-primary svelte-16m7f8c\">Add Account</button></div></div>"), _i = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-16m7f8c\">Authenticated</span>"), vi = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-16m7f8c\">Pending Auth</span>"), yi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-16m7f8c\">Active</span>"), bi = /* @__PURE__ */ Q("<div class=\"account-item svelte-16m7f8c\"><div class=\"account-info svelte-16m7f8c\"><div class=\"account-name svelte-16m7f8c\"> </div> <div class=\"account-badges svelte-16m7f8c\"><!> <!></div></div> <div class=\"account-actions svelte-16m7f8c\"><button class=\"link-btn svelte-16m7f8c\"> </button> <div class=\"switch-container\"><label class=\"switch svelte-16m7f8c\"><input type=\"checkbox\" class=\"svelte-16m7f8c\"/> <span class=\"slider round svelte-16m7f8c\"></span></label></div> <button class=\"btn-danger-icon svelte-16m7f8c\" title=\"Delete Account\">✕</button></div></div>"), xi = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-16m7f8c\">No Spotify accounts connected.</div>"), Si = /* @__PURE__ */ Q("<div class=\"settings-section svelte-16m7f8c\"><div class=\"section-header svelte-16m7f8c\"><h3 class=\"section-title svelte-16m7f8c\">Global Credentials</h3> <button class=\"btn-ghost svelte-16m7f8c\"> </button></div> <!></div> <hr class=\"divider svelte-16m7f8c\"/> <div class=\"settings-section svelte-16m7f8c\"><div class=\"section-header svelte-16m7f8c\"><h3 class=\"section-title svelte-16m7f8c\"> </h3> <!></div> <!> <div class=\"accounts-list svelte-16m7f8c\"></div></div>", 1), Ci = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-16m7f8c\"><div class=\"card-header svelte-16m7f8c\"><div class=\"header-left svelte-16m7f8c\"><h2 class=\"card-title svelte-16m7f8c\">Spotify</h2> <span class=\"type-badge svelte-16m7f8c\">Streaming Service</span></div></div> <!></section>"), wi = {
	hash: "svelte-16m7f8c",
	code: ".plugin-card.svelte-16m7f8c {background:var(--bg-surface, #0f172a);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));border-radius:var(--radius, 16px);padding:28px;color:var(--text-primary, #f8fafc);font-family:'Inter', sans-serif;box-shadow:0 4px 24px rgba(0, 0, 0, 0.2);transition:transform 0.2s ease;}.card-header.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));}.header-left.svelte-16m7f8c {display:flex;align-items:center;gap:16px;}.card-title.svelte-16m7f8c {margin:0;font-size:22px;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg, #fff 0%, #a5b4fc 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}.type-badge.svelte-16m7f8c {font-size:10px;padding:4px 10px;background:rgba(20, 184, 166, 0.1);color:var(--color-primary, #14b8a6);border:1px solid rgba(20, 184, 166, 0.2);border-radius:20px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;}.settings-section.svelte-16m7f8c {margin-bottom:32px;}.section-header.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}.section-title.svelte-16m7f8c {margin:0;font-size:14px;font-weight:700;color:var(--text-secondary, #94a3b8);text-transform:uppercase;letter-spacing:0.05em;}.form-grid.svelte-16m7f8c {display:grid;grid-template-columns:1fr;gap:20px;}\n\n  @media (min-width: 640px) {.form-grid.svelte-16m7f8c {grid-template-columns:1fr 1fr;}.actions-row.svelte-16m7f8c {grid-column:span 2;}\n  }.form-field.svelte-16m7f8c {display:flex;flex-direction:column;gap:10px;}.field-label.svelte-16m7f8c {font-size:12px;font-weight:600;color:var(--text-secondary, #94a3b8);opacity:0.8;}.input-field.svelte-16m7f8c {width:100%;padding:14px 18px;background:var(--bg-input, #1e293b);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));border-radius:12px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.25s cubic-bezier(0.4, 0, 0.2, 1);}.input-field.svelte-16m7f8c:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 4px rgba(20, 184, 166, 0.15);background:rgba(255, 255, 255, 0.03);}.input-field.readonly.svelte-16m7f8c {opacity:0.6;cursor:not-allowed;background:rgba(255, 255, 255, 0.02);}.helper-text.svelte-16m7f8c {font-size:11px;color:var(--text-muted, #64748b);margin-top:6px;font-style:italic;}.btn-primary.svelte-16m7f8c {padding:12px 28px;background:var(--color-primary, #14b8a6);color:#000;border:none;border-radius:12px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-16m7f8c:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 6px 20px rgba(20, 184, 166, 0.3);}.btn-primary.svelte-16m7f8c:active:not(:disabled) {transform:translateY(0);}.btn-primary.svelte-16m7f8c:disabled {opacity:0.4;cursor:not-allowed;box-shadow:none;}.btn-ghost.svelte-16m7f8c {padding:10px 18px;background:rgba(255, 255, 255, 0.05);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));color:var(--text-primary, #f8fafc);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s ease;}.btn-ghost.svelte-16m7f8c:hover {background:rgba(255, 255, 255, 0.1);border-color:rgba(255, 255, 255, 0.2);transform:translateY(-1px);}.divider.svelte-16m7f8c {border:none;border-top:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));margin:32px 0;opacity:0.3;}.accounts-list.svelte-16m7f8c {display:flex;flex-direction:column;gap:14px;}.account-item.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;padding:20px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));border-radius:16px;transition:all 0.3s ease;}.account-item.svelte-16m7f8c:hover {border-color:rgba(20, 184, 166, 0.3);background:rgba(255, 255, 255, 0.05);transform:translateX(4px);}.account-info.svelte-16m7f8c {display:flex;flex-direction:column;gap:8px;}.account-name.svelte-16m7f8c {font-weight:700;font-size:16px;color:#fff;}.account-badges.svelte-16m7f8c {display:flex;gap:10px;}.status-badge.svelte-16m7f8c {font-size:10px;padding:3px 10px;border-radius:6px;font-weight:800;text-transform:uppercase;letter-spacing:0.03em;}.status-badge.success.svelte-16m7f8c {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-16m7f8c {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.status-badge.active.svelte-16m7f8c {background:rgba(20, 184, 166, 0.1);color:var(--color-primary, #14b8a6);border:1px solid rgba(20, 184, 166, 0.2);}.account-actions.svelte-16m7f8c {display:flex;gap:20px;align-items:center;}.link-btn.svelte-16m7f8c {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:700;cursor:pointer;padding:0;transition:opacity 0.2s;}.link-btn.svelte-16m7f8c:hover {opacity:0.8;text-decoration:underline;}.btn-danger-icon.svelte-16m7f8c {background:rgba(239, 68, 68, 0.1);color:#ef4444;border:1px solid rgba(239, 68, 68, 0.2);width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 0.2s ease;font-size:16px;}.btn-danger-icon.svelte-16m7f8c:hover {background:#ef4444;color:#fff;transform:rotate(90deg);}\n\n  /* Switch Component */.switch.svelte-16m7f8c {position:relative;display:inline-block;width:44px;height:24px;}.switch.svelte-16m7f8c input:where(.svelte-16m7f8c) {opacity:0;width:0;height:0;}.slider.svelte-16m7f8c {position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:rgba(255, 255, 255, 0.1);transition:.4s;border:1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));}.slider.svelte-16m7f8c:before {position:absolute;content:\"\";height:18px;width:18px;left:2px;bottom:2px;background-color:#94a3b8;transition:.4s;box-shadow:0 2px 4px rgba(0,0,0,0.2);}input.svelte-16m7f8c:checked + .slider:where(.svelte-16m7f8c) {background-color:var(--color-primary, #14b8a6);border-color:var(--color-primary, #14b8a6);}input.svelte-16m7f8c:checked + .slider:where(.svelte-16m7f8c):before {transform:translateX(20px);background-color:white;}.slider.round.svelte-16m7f8c {border-radius:34px;}.slider.round.svelte-16m7f8c:before {border-radius:50%;}.loading-state.svelte-16m7f8c {display:flex;flex-direction:column;align-items:center;gap:20px;padding:60px;color:var(--text-muted, #64748b);}.spinner.svelte-16m7f8c {width:40px;height:40px;border:4px solid rgba(20, 184, 166, 0.1);border-top-color:var(--color-primary, #14b8a6);border-radius:50%;\n    animation: svelte-16m7f8c-spin 0.8s cubic-bezier(0.5, 0, 0.5, 1) infinite;}\n\n  @keyframes svelte-16m7f8c-spin {\n    to { transform: rotate(360deg); }\n  }.add-account-form.svelte-16m7f8c {background:rgba(255, 255, 255, 0.02);padding:20px;border-radius:16px;border:1px dashed var(--border-subtle, rgba(255, 255, 255, 0.1));margin-bottom:24px;\n    animation: svelte-16m7f8c-fadeIn 0.3s ease-out;}\n\n  @keyframes svelte-16m7f8c-fadeIn {\n    from { opacity: 0; transform: translateY(-10px); }\n    to { opacity: 1; transform: translateY(0); }\n  }.empty-accounts.svelte-16m7f8c {text-align:center;padding:40px;background:rgba(255, 255, 255, 0.02);border-radius:16px;border:1px dashed var(--border-subtle, rgba(255, 255, 255, 0.1));color:var(--text-muted, #64748b);font-style:italic;}"
};
function Ti(e, t) {
	qe(t, !1), Gr(e, wi);
	let n = oi(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P([]), s = /* @__PURE__ */ P(!1), c = /* @__PURE__ */ P(""), l = /* @__PURE__ */ P(!0), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1);
	Mr(async () => {
		n(n().replace(/\/$/, "")), await f(), await m(), !X(a) && typeof window < "u" && F(a, `${window.location.protocol}//${window.location.host}/api/spotify/callback`), F(d, !!(X(r) && X(i) && X(a) && X(o).some((e) => e.is_authenticated))), F(l, !1);
	});
	async function f() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (F(r, e.settings.client_id || ""), F(i, e.settings.client_secret || ""), F(a, e.settings.redirect_uri || ""));
		} catch (e) {
			console.error("Failed to load Spotify settings:", e);
		}
	}
	async function p() {
		if (!X(r) || !X(i)) {
			alert("Client ID and Secret are required");
			return;
		}
		try {
			if (F(u, !0), !(await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					client_id: X(r),
					client_secret: X(i),
					redirect_uri: X(a)
				})
			})).ok) throw Error("Save failed");
			console.log("Spotify credentials saved");
		} catch (e) {
			console.error("Failed to save Spotify settings:", e), alert("Failed to save settings. Check console.");
		} finally {
			F(u, !1);
		}
	}
	async function m() {
		try {
			F(o, (await (await fetch(`${n()}/accounts`)).json())?.accounts || []);
		} catch (e) {
			console.error("Failed to load Spotify accounts:", e), F(o, []);
		}
	}
	async function h() {
		if (X(c).trim()) {
			if (X(o).length >= 25) {
				alert("Maximum 25 accounts allowed");
				return;
			}
			try {
				if (!(await fetch(`${n()}/accounts`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						account_name: X(c),
						display_name: X(c)
					})
				})).ok) throw Error("Add failed");
				F(c, ""), F(s, !1), await m();
			} catch (e) {
				console.error("Failed to add account:", e);
			}
		}
	}
	async function g(e, t) {
		try {
			if (!(await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			})).ok) throw Error("Toggle failed");
			await m();
		} catch (e) {
			console.error("Failed to toggle account:", e);
		}
	}
	async function _(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			if (!(await fetch(`${n()}/accounts/${e}`, { method: "DELETE" })).ok) throw Error("Delete failed");
			await m();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function v(e) {
		if (!X(r) || !X(i)) {
			alert("Please save Client ID and Secret first.");
			return;
		}
		try {
			await p();
			let t = await (await fetch(`${n()}/auth?account_id=${e}`)).json();
			t?.auth_url && (window.open(t.auth_url, "_blank", "noopener,noreferrer"), setTimeout(() => m(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), bt();
		}
	};
	ii();
	var b = Ci(), x = R(L(b), 2), S = (e) => {
		$(e, pi());
	}, C = (e) => {
		var t = Si(), n = ln(t), l = L(n), f = R(L(l), 2), m = L(f, !0);
		O(f), O(l);
		var y = R(l, 2), b = (e) => {
			var t = mi(), n = L(t), o = R(L(n), 2);
			Yr(o), O(n);
			var s = R(n, 2), c = R(L(s), 2), l = L(c);
			Yr(l), O(c), O(s);
			var d = R(s, 2), f = R(L(d), 2);
			Yr(f), Be(2), O(d);
			var m = R(d, 2), h = L(m), g = L(h, !0);
			O(h), O(m), O(t), An(() => {
				h.disabled = X(u), wr(g, X(u) ? "Saving..." : "Save Credentials");
			}), ti(o, () => X(r), (e) => F(r, e)), ti(l, () => X(i), (e) => F(i, e)), ti(f, () => X(a), (e) => F(a, e)), hr("click", h, p), $(e, t);
		};
		Pr(y, (e) => {
			X(d) || e(b);
		}), O(n);
		var x = R(n, 4), S = L(x), C = L(S), w = L(C);
		O(C);
		var ee = R(C, 2), te = (e) => {
			var t = hi(), n = L(t, !0);
			O(t), An(() => wr(n, X(s) ? "Cancel" : "+ Add Account")), hr("click", t, () => F(s, !X(s))), $(e, t);
		};
		Pr(ee, (e) => {
			X(o), Z(() => X(o).length < 25) && e(te);
		}), O(S);
		var ne = R(S, 2), re = (e) => {
			var t = gi(), n = L(t), r = L(n);
			Yr(r), O(n);
			var i = R(n, 2), a = L(i);
			O(i), O(t), ti(r, () => X(c), (e) => F(c, e)), hr("keydown", r, (e) => e.key === "Enter" && h()), hr("click", a, h), $(e, t);
		};
		Pr(ne, (e) => {
			X(s) && e(re);
		});
		var ie = R(ne, 2);
		zr(ie, 5, () => X(o), Fr, (e, t) => {
			var n = bi(), r = L(n), i = L(r), a = L(i, !0);
			O(i);
			var o = R(i, 2), s = L(o), c = (e) => {
				$(e, _i());
			}, l = (e) => {
				$(e, vi());
			};
			Pr(s, (e) => {
				X(t), Z(() => X(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				$(e, yi());
			};
			Pr(u, (e) => {
				X(t), Z(() => X(t).is_active) && e(d);
			}), O(o), O(r);
			var f = R(r, 2), p = L(f), m = L(p, !0);
			O(p);
			var h = R(p, 2), y = L(h), b = L(y);
			Yr(b), Be(2), O(y), O(h);
			var x = R(h, 2);
			O(f), O(n), An(() => {
				wr(a, (X(t), Z(() => X(t).display_name || X(t).account_name))), wr(m, (X(t), Z(() => X(t).is_authenticated ? "Re-auth" : "Authorize"))), Xr(b, (X(t), Z(() => X(t).is_active)));
			}), hr("click", p, () => v(X(t).id)), hr("change", b, () => g(X(t).id, X(t).is_active)), hr("click", x, () => _(X(t).id, X(t).display_name || X(t).account_name)), $(e, n);
		}, (e) => {
			$(e, xi());
		}), O(ie), O(x), An(() => {
			wr(m, X(d) ? "Expand" : "Collapse"), wr(w, `Accounts (${(X(o), Z(() => X(o).length)) ?? ""}/25)`);
		}), hr("click", f, () => F(d, !X(d))), $(e, t);
	};
	return Pr(x, (e) => {
		X(l) ? e(S) : e(C, -1);
	}), O(b), $(e, b), Je(y);
}
customElements.define("spotify-dashboard-card", fi(Ti, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { Ti as default };
